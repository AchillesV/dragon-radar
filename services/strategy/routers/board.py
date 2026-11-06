"""
「打板」路由 —— 打板策略选股（预选 / 最终两阶段）

算法口径来自 QMT 打板策略（打板1）的选股层，只保留可用于日线复现的部分：
  1. 股票池：主板（600/601/603/605/000/001/002/003），剔除科创板 688、创业板
     300/301、北交所与 ST。
  2. 首板：涨停日当天涨停、前一交易日未涨停（连板数 = 1）。
  3. 剔除一字板（开盘与收盘均贴在涨停价）。
  4. 黑名单：首板日收盘偏离 MA20 > 30%；近 10 个交易日涨停次数 >= 4。

两阶段：
  - 预选（pre）：收盘后基于「当日首板」套用规则 1~4，给出下一交易日的预选池，
    不应用开盘涨幅过滤与排序（规则 5、6 需要次日开盘价，尚不可知）。
  - 最终（final）：次日 09:30 后基于「昨日首板」+ 当日开盘价，套用规则 1~6，
    开盘涨幅 ∈ [-10%, -4%)，并按开盘涨幅升序排名，第 1 名为策略首选。
    用户点击「重新计算」会立即触发最终计算；未点击时服务端 09:30 后自动计算。
    只有最终结果落库（SQLite），保留最近 10 个交易日。

说明：
  - 原策略依赖 QMT 分钟数据剔除「昨日 14:10 后首次触板」的股票；分钟数据在
    服务端不可得，按原策略兜底口径「无法判断则不剔除」处理，因此本模块不做该项过滤。
  - 价格口径使用腾讯日线（不复权），对绝大多数交易日与 QMT 前复权判定一致。
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter

import board_store
from models import BoardPick, BoardStageResult
from routers.screening import _fetch_hist_tencent, _HIST_CACHE
from routers.trend import _get_session_date, _get_universe

try:
    from zoneinfo import ZoneInfo

    _TZ = ZoneInfo("Asia/Shanghai")
except Exception:  # 本地缺少 tzdata 时退回服务器本地时间
    _TZ = None

logger = logging.getLogger(__name__)
router = APIRouter()

# 主板前缀（与 QMT 策略 Cfg.MAIN_BOARD 一致）
MAIN_BOARD_PREFIX = ("600", "601", "603", "605", "000", "001", "002", "003")

# 算法阈值（与 QMT 策略 Cfg 对齐）
LIMIT_PCT_MAIN = 0.10
LIMIT_TOL = 0.001
YIZI_TOL = 0.001
BAN_HIGH_DEV_THR = 0.30
BAN_HIGH_DEV_N = 20
BAN_MANY_BOARDS_N = 10
BAN_MANY_BOARDS_THR = 4
BAN_LIMIT_TICK = 0.005
OPEN_PCT_MIN = -0.10
OPEN_PCT_MAX = -0.040
OPEN_PCT_TOL = 1e-6

# 交易时段（北京时间，分钟数）：09:30 开盘、15:00 收盘
OPEN_TIME_MIN = 9 * 60 + 30
CLOSE_TIME_MIN = 15 * 60
AUTO_CHECK_INTERVAL = 60  # 秒

MAX_WORKERS = 20
PRE_CACHE_TTL = 60  # 预选结果短缓存，避免同一分钟内重复全量扫描

# 自动最终计算完成后标记日期，避免同一天重复扫描
_auto_finalized_date: Optional[str] = None
_pre_cache: dict = {"key": None, "ts": 0.0, "value": None}


def _is_main_board(code: str) -> bool:
    return str(code)[:3] in MAIN_BOARD_PREFIX


def _is_st_name(name: str) -> bool:
    return "ST" in str(name).upper()


def _safe_int(v) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _limit_up_price(base_close: float) -> float:
    if base_close <= 0:
        return 0.0
    return round(base_close * (1.0 + LIMIT_PCT_MAIN) + 1e-9, 2)


def _is_limit_up(close_px: float, base_close: float) -> bool:
    if close_px <= 0 or base_close <= 0:
        return False
    lu = _limit_up_price(base_close)
    return close_px >= lu * (1.0 - LIMIT_TOL)


def _is_limit_up_tick(close_px: float, base_close: float) -> bool:
    if close_px <= 0 or base_close <= 0:
        return False
    lu = _limit_up_price(base_close)
    return close_px >= lu - BAN_LIMIT_TICK - 1e-9


def _now_cn() -> datetime:
    return datetime.now(_TZ) if _TZ else datetime.now()


def _next_weekday(date_str: str) -> str:
    """下一交易日（仅跳过周末；法定节假日无法预知，按最近工作日估算）。"""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _fresh_session_date() -> str:
    """绕过 1 小时日线缓存，确保盘中能及时识别当日 K 线。"""
    _HIST_CACHE.pop("600000", None)
    return _get_session_date()


def _last_two_sessions() -> Optional[Tuple[str, str]]:
    """返回 (T-1, T) 两个交易日（以 600000 最后一根日线为最新交易日）。"""
    df = _fetch_hist_tencent("600000", days=8)
    if df is None or df.empty or len(df) < 2:
        return None
    dates = [str(x) for x in df["日期"].tolist()]
    return dates[-2], dates[-1]


def _market_phase() -> Tuple[str, str, bool]:
    """
    返回 (最新交易日, 今天, 是否处于「当日最终」窗口)。
    最终窗口：最新交易日 = 今天，且 09:30 <= 当前时间 < 15:00。
    其余时间展示下一交易日的预选。
    """
    now = _now_cn()
    today = now.strftime("%Y-%m-%d")
    hm = now.hour * 60 + now.minute
    session = _fresh_session_date()
    final_window = (session == today and OPEN_TIME_MIN <= hm < CLOSE_TIME_MIN)
    return session, today, final_window


def _get_candidate_pool(board_date: str) -> Optional[List[Tuple[str, str, Optional[str]]]]:
    """
    取指定交易日的涨停池，筛出主板首板（连板数 == 1）作为候选。
    数据源异常返回 None，由调用方决定是否回退全市场扫描。
    """
    try:
        import akshare as ak

        df = ak.stock_zt_pool_em(date=str(board_date).replace("-", ""))
    except Exception as e:
        logger.warning(f"打板：涨停池获取失败 {board_date}: {e}")
        return None
    if df is None or df.empty:
        return None

    pool: List[Tuple[str, str, Optional[str]]] = []
    for _, r in df.iterrows():
        code = str(r.get("代码", "")).strip().zfill(6)
        name = str(r.get("名称", "")).strip()
        if not code or not _is_main_board(code) or _is_st_name(name):
            continue
        if _safe_int(r.get("连板数", 0)) != 1:
            continue
        industry = str(r.get("所属行业", "") or "").strip() or None
        pool.append((code, name, industry))
    return pool


def _full_market_pool() -> List[Tuple[str, str, Optional[str]]]:
    """回退：用全市场股票池（已剔除创业板/科创板/ST），只保留主板。"""
    return [
        (code, name, None)
        for code, name in _get_universe()
        if _is_main_board(code) and not _is_st_name(name)
    ]


def _fetch_hist_full(code: str, days: int = 30):
    """取足够长的日线；若缓存里只有短周期数据（如交易日判定用的 5 日），清缓存重取。"""
    need = BAN_HIGH_DEV_N + 1
    df = _fetch_hist_tencent(code, days=days)
    if df is not None and len(df) >= need:
        return df
    _HIST_CACHE.pop(code, None)
    return _fetch_hist_tencent(code, days=days)


def _evaluate_final(code: str, name: str, industry: Optional[str], t_date: str) -> Optional[dict]:
    """最终口径：首板日 = T-1，按 T 日开盘涨幅筛选。"""
    df = _fetch_hist_full(code)
    if df is None or df.empty or len(df) < BAN_HIGH_DEV_N + 1:
        return None

    dates = [str(x) for x in df["日期"].tolist()]
    # 当日无 K 线（停牌/未开盘）直接跳过
    if dates[-1] != t_date:
        return None

    closes = [float(x) for x in df["收盘"].tolist()]
    opens = [float(x) for x in df["开盘"].tolist()]
    volumes = [float(x) for x in df["成交量"].tolist()]

    c_t1 = closes[-2]   # T-1 收盘（首板日）
    c_t2 = closes[-3]   # T-2 收盘
    c_t3 = closes[-4]   # T-3 收盘
    if c_t1 <= 0 or c_t2 <= 0 or c_t3 <= 0:
        return None

    # 1) 昨日首板：T-1 涨停，T-2 未涨停
    if not _is_limit_up(c_t1, c_t2):
        return None
    if _is_limit_up(c_t2, c_t3):
        return None

    # 2) 剔除昨日一字板（开盘、收盘双封）
    lu_t1 = _limit_up_price(c_t2)
    o_t1 = opens[-2]
    if lu_t1 > 0 and o_t1 >= lu_t1 * (1.0 - YIZI_TOL) and c_t1 >= lu_t1 * (1.0 - YIZI_TOL):
        return None

    # 3) 黑名单 1：T-1 收盘偏离 MA20 超过 30%
    ma20 = sum(closes[-(BAN_HIGH_DEV_N + 1):-1]) / float(BAN_HIGH_DEV_N)
    if ma20 > 0 and c_t1 / ma20 - 1.0 > BAN_HIGH_DEV_THR + 1e-9:
        return None

    # 4) 黑名单 2：近 10 个交易日（截至 T-1）涨停次数 >= 4
    boards = 0
    for k in range(1, BAN_MANY_BOARDS_N + 1):
        cur = closes[-1 - k]
        prv = closes[-2 - k]
        if cur <= 0 or prv <= 0:
            continue
        if (cur / prv - 1.0) > LIMIT_PCT_MAIN + 0.05:
            continue
        if _is_limit_up_tick(cur, prv):
            boards += 1
    if boards >= BAN_MANY_BOARDS_THR:
        return None

    # 5) 今日开盘涨幅区间 [-10%, -4%)
    o_t = opens[-1]
    if o_t <= 0:
        return None
    open_pct = o_t / c_t1 - 1.0
    if open_pct < OPEN_PCT_MIN - OPEN_PCT_TOL:
        return None
    if open_pct >= OPEN_PCT_MAX - OPEN_PCT_TOL:
        return None

    change_pct = closes[-1] / c_t1 - 1.0 if c_t1 > 0 else 0.0
    return {
        "code": code,
        "name": name,
        "industry": industry,
        "open_pct": round(open_pct * 100, 2),
        "price": round(o_t, 2),
        "close": round(closes[-1], 2) if closes[-1] > 0 else None,
        "prev_close": round(c_t1, 2),
        "change_pct": round(change_pct * 100, 2),
        "volume": volumes[-1] if volumes else None,
        "limit_up_date": dates[-2],
    }


def _evaluate_pre(code: str, name: str, industry: Optional[str], t_date: str) -> Optional[dict]:
    """预选口径：首板日 = t_date（最新交易日），只套用规则 1~4，不应用开盘涨幅与排序。"""
    df = _fetch_hist_full(code)
    if df is None or df.empty or len(df) < BAN_HIGH_DEV_N + 1:
        return None

    dates = [str(x) for x in df["日期"].tolist()]
    closes = [float(x) for x in df["收盘"].tolist()]
    opens = [float(x) for x in df["开盘"].tolist()]
    volumes = [float(x) for x in df["成交量"].tolist()]

    # 若日线已包含 t_date 之后的 K 线（如开盘前拿到了当日占位 K 线），回溯截断
    if dates[-1] > t_date:
        cut = sum(1 for d in dates if d <= t_date)
        if cut < BAN_HIGH_DEV_N + 1:
            return None
        dates, closes, opens, volumes = dates[:cut], closes[:cut], opens[:cut], volumes[:cut]
    if dates[-1] != t_date:
        return None

    c_t = closes[-1]    # T 收盘（首板日）
    c_t1 = closes[-2]   # T-1 收盘
    c_t2 = closes[-3]   # T-2 收盘
    if c_t <= 0 or c_t1 <= 0 or c_t2 <= 0:
        return None

    # 1) 首板：T 涨停，T-1 未涨停
    if not _is_limit_up(c_t, c_t1):
        return None
    if _is_limit_up(c_t1, c_t2):
        return None

    # 2) 剔除一字板（T 开盘、收盘双封）
    lu_t = _limit_up_price(c_t1)
    if lu_t > 0 and opens[-1] >= lu_t * (1.0 - YIZI_TOL) and c_t >= lu_t * (1.0 - YIZI_TOL):
        return None

    # 3) 黑名单 1：T 收盘偏离 MA20 超过 30%
    ma20 = sum(closes[-(BAN_HIGH_DEV_N + 1):-1]) / float(BAN_HIGH_DEV_N)
    if ma20 > 0 and c_t / ma20 - 1.0 > BAN_HIGH_DEV_THR + 1e-9:
        return None

    # 4) 黑名单 2：近 10 个交易日（截至 T）涨停次数 >= 4
    boards = 0
    for k in range(0, BAN_MANY_BOARDS_N):
        cur = closes[-1 - k]
        prv = closes[-2 - k]
        if cur <= 0 or prv <= 0:
            continue
        if (cur / prv - 1.0) > LIMIT_PCT_MAIN + 0.05:
            continue
        if _is_limit_up_tick(cur, prv):
            boards += 1
    if boards >= BAN_MANY_BOARDS_THR:
        return None

    change_pct = c_t / c_t1 - 1.0 if c_t1 > 0 else 0.0
    return {
        "code": code,
        "name": name,
        "industry": industry,
        "open_pct": None,
        "price": None,
        "close": round(c_t, 2),
        "prev_close": round(c_t1, 2),
        "change_pct": round(change_pct * 100, 2),
        "volume": volumes[-1] if volumes else None,
        "limit_up_date": dates[-1],
    }


def _batch_evaluate(
    cands: List[Tuple[str, str, Optional[str]]], t_date: str, mode: str
) -> List[dict]:
    results: List[dict] = []
    if not cands:
        return results
    fn = _evaluate_pre if mode == "pre" else _evaluate_final
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futs = {
            pool.submit(fn, code, name, industry, t_date): code
            for code, name, industry in cands
        }
        for fut in futs:
            try:
                m = fut.result()
                if m:
                    results.append(m)
            except Exception as e:
                logger.debug(f"打板评估失败 {futs[fut]}: {e}")
    return results


def _compute_board_picks() -> Optional[Tuple[str, List[BoardPick]]]:
    """最终选股：最新交易日 T 的最终结果。返回 (选股日, 结果)；无法确定交易日返回 None。"""
    sessions = _last_two_sessions()
    if not sessions:
        return None
    t1_date, t_date = sessions

    pool = _get_candidate_pool(t1_date)
    if pool is None:
        logger.info("打板：涨停池不可用，回退全市场扫描")
        pool = _full_market_pool()

    matches = _batch_evaluate(pool, t_date, mode="final")
    matches.sort(key=lambda m: m["open_pct"])

    picks: List[BoardPick] = []
    for i, m in enumerate(matches, start=1):
        desc = (
            f"{m['limit_up_date']} 首板涨停；今日开盘涨幅 {m['open_pct']:+.2f}%；"
            f"按开盘涨幅升序排名第 {i} 名"
        )
        if i == 1:
            desc += "（策略首选）"
        picks.append(
            BoardPick(
                date=t_date,
                stage="final",
                code=m["code"],
                name=m["name"],
                rank=i,
                is_top=(i == 1),
                open_pct=m["open_pct"],
                price=m["price"],
                close=m["close"],
                prev_close=m["prev_close"],
                change_pct=m["change_pct"],
                volume=m["volume"],
                industry=m["industry"],
                limit_up_date=m["limit_up_date"],
                description=desc,
            )
        )
    return t_date, picks


def _compute_pre_picks(force: bool = False) -> Optional[Tuple[str, str, List[BoardPick]]]:
    """
    预选：基于最新交易日 T 的首板，套用规则 1~4，给出下一交易日的预选池。
    返回 (下一交易日, T, 结果)。
    """
    sessions = _last_two_sessions()
    if not sessions:
        return None
    t1_date, t_date = sessions

    now_dt = _now_cn()
    hm = now_dt.hour * 60 + now_dt.minute
    # 开盘前若已出现今日占位 K 线，预选应基于上一交易日首板
    source_date = t1_date if (t_date == now_dt.strftime("%Y-%m-%d") and hm < OPEN_TIME_MIN) else t_date

    now = time.time()
    if (
        not force
        and _pre_cache["key"] == source_date
        and _pre_cache["value"] is not None
        and now - _pre_cache["ts"] < PRE_CACHE_TTL
    ):
        return _pre_cache["value"]

    pool = _get_candidate_pool(source_date)
    if pool is None:
        logger.info("打板预选：涨停池不可用，回退全市场扫描")
        pool = _full_market_pool()

    matches = _batch_evaluate(pool, source_date, mode="pre")
    # 规则 6（按开盘涨幅排序）不应用于预选，这里按代码稳定排序便于展示
    matches.sort(key=lambda m: m["code"])

    target_date = _next_weekday(source_date)
    picks: List[BoardPick] = []
    for i, m in enumerate(matches, start=1):
        picks.append(
            BoardPick(
                date=target_date,
                stage="pre",
                code=m["code"],
                name=m["name"],
                rank=i,
                is_top=False,
                open_pct=None,
                price=None,
                close=m["close"],
                prev_close=m["prev_close"],
                change_pct=m["change_pct"],
                volume=m["volume"],
                industry=m["industry"],
                limit_up_date=m["limit_up_date"],
                description=(
                    f"{m['limit_up_date']} 首板涨停；预选未应用次日开盘涨幅过滤，"
                    f"待 {target_date} 09:30 后自动确认"
                ),
            )
        )
    result = (target_date, source_date, picks)
    _pre_cache.update(key=source_date, ts=now, value=result)
    return result


def _auto_finalize_if_due() -> None:
    """09:30 后自动完成当日最终计算并落库（每天最多一次）。"""
    global _auto_finalized_date

    now = _now_cn()
    hm = now.hour * 60 + now.minute
    # 只在交易时段附近做网络检查，避免全天无谓请求
    if now.weekday() >= 5 or not (OPEN_TIME_MIN - 5 <= hm <= CLOSE_TIME_MIN + 5):
        return
    if _auto_finalized_date == now.strftime("%Y-%m-%d"):
        return

    _session, today, final_window = _market_phase()
    if not final_window:
        return
    if _auto_finalized_date == today:
        return
    if board_store.has_snapshot(today):
        _auto_finalized_date = today
        return

    computed = _compute_board_picks()
    if computed is None:
        return
    trade_date, picks = computed
    board_store.save_snapshot(trade_date, picks)
    _auto_finalized_date = trade_date
    logger.info(f"打板：09:30 后自动完成 {trade_date} 最终选股，{len(picks)} 只")


async def auto_final_loop() -> None:
    """后台任务：每隔 60 秒检查是否到达最终计算时间。"""
    while True:
        try:
            await asyncio.to_thread(_auto_finalize_if_due)
        except Exception as e:
            logger.warning(f"打板自动计算异常: {e}")
        await asyncio.sleep(AUTO_CHECK_INTERVAL)


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

def _stage_result(stage: str, target: str, source: str, picks: List[BoardPick]) -> BoardStageResult:
    return BoardStageResult(
        stage=stage, target_date=target, source_date=source, picks=picks
    )


@router.get("/preselection", response_model=BoardStageResult)
async def get_board_preselection():
    """
    默认视图：
    - 盘中 09:30~15:00（当日 K 线已生成）：返回当日最终选股（规则 1~6）。
    - 其余时间（开盘前 / 收盘后 / 非交易日）：返回下一交易日的预选（规则 1~4）。
    """
    session, today, final_window = _market_phase()

    if final_window:
        if board_store.has_snapshot(today):
            return _stage_result("final", today, today, board_store.load_snapshot(today))
        computed = _compute_board_picks()
        if computed:
            trade_date, picks = computed
            board_store.save_snapshot(trade_date, picks)
            return _stage_result("final", trade_date, trade_date, picks)
        return _stage_result("final", today, today, [])

    computed_pre = _compute_pre_picks()
    if computed_pre is None:
        return _stage_result("pre", _next_weekday(session), session, [])
    target_date, source_date, picks = computed_pre
    return _stage_result("pre", target_date, source_date, picks)


@router.get("/candidates", response_model=List[BoardPick])
async def get_board_candidates(date: Optional[str] = None):
    """
    历史最终选股。

    - 传 date=YYYY-MM-DD：只读历史快照，不触发扫描。
    - 不传 date：取数据库中最新的最终快照；没有则按当日最终计算并落库。
    """
    if date:
        return board_store.load_snapshot(date)

    session = _get_session_date()
    if board_store.has_snapshot(session):
        return board_store.load_snapshot(session)

    computed = _compute_board_picks()
    if computed is None:
        return []
    trade_date, picks = computed
    board_store.save_snapshot(trade_date, picks)
    return picks


@router.post("/sync", response_model=BoardStageResult)
async def sync_board_candidates():
    """
    手动重新计算。
    - 盘中：立即按规则 1~6 计算当日最终结果并覆盖落库。
    - 非盘中：重新计算下一交易日的预选（不应用规则 5、6，不落库）。
    """
    session, today, final_window = _market_phase()

    if final_window:
        computed = _compute_board_picks()
        if computed:
            trade_date, picks = computed
            board_store.save_snapshot(trade_date, picks)
            return _stage_result("final", trade_date, trade_date, picks)
        return _stage_result("final", today, today, [])

    computed_pre = _compute_pre_picks(force=True)
    if computed_pre is None:
        return _stage_result("pre", _next_weekday(session), session, [])
    target_date, source_date, picks = computed_pre
    return _stage_result("pre", target_date, source_date, picks)


@router.get("/dates", response_model=List[str])
async def get_board_dates():
    """最近 10 个有最终快照的交易日（倒序）。"""
    return board_store.list_dates(limit=board_store.KEEP_DAYS)

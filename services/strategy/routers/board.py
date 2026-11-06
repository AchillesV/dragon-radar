"""
「打板」路由 —— 打板策略每日选股

算法口径来自 QMT 打板策略（打板1）的选股层，只保留可用于日线复现的部分：
  1. 股票池：主板（600/601/603/605/000/001/002/003），剔除科创板 688、创业板
     300/301、北交所与 ST。
  2. 昨日首板：T-1 涨停且 T-2 未涨停（连板数 = 1）。
  3. 剔除昨日一字板（T-1 开盘与收盘均贴在涨停价）。
  4. 黑名单：T-1 收盘偏离 MA20 > 30%；近 10 个交易日涨停次数 >= 4。
  5. 开盘涨幅：仅保留 T 日开盘涨幅 ∈ [-10%, -4%) 的股票（低开区间）。
  6. 按 T 日开盘涨幅升序排名，第 1 名为策略首选。

说明：
  - 原策略依赖 QMT 分钟数据剔除「昨日 14:10 后首次触板」的股票；分钟数据在
    服务端不可得，按原策略兜底口径「无法判断则不剔除」处理，因此本模块不做该项过滤。
  - 价格口径使用腾讯日线（不复权），对绝大多数交易日与 QMT 前复权判定一致。

每个交易日结果落库（SQLite），只保留最近 10 个交易日。
"""
import logging
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter

import board_store
from models import BoardPick
from routers.screening import _fetch_hist_tencent, _HIST_CACHE
from routers.trend import _get_session_date, _get_universe

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

MAX_WORKERS = 20
_CACHE_TTL = 60


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


def _last_two_sessions() -> Optional[Tuple[str, str]]:
    """返回 (T-1, T) 两个交易日（以 600000 最后一根日线为最新交易日）。"""
    df = _fetch_hist_tencent("600000", days=8)
    if df is None or df.empty or len(df) < 2:
        return None
    dates = [str(x) for x in df["日期"].tolist()]
    return dates[-2], dates[-1]


def _get_candidate_pool(t1_date: str) -> Optional[List[Tuple[str, str, Optional[str]]]]:
    """
    取 T-1 的昨日涨停池，筛出主板首板（连板数 == 1）作为候选。
    数据源异常返回 None，由调用方决定是否回退全市场扫描。
    """
    try:
        import akshare as ak

        df = ak.stock_zt_pool_em(date=str(t1_date).replace("-", ""))
    except Exception as e:
        logger.warning(f"打板：昨日涨停池获取失败 {t1_date}: {e}")
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


def _evaluate(code: str, name: str, industry: Optional[str], t_date: str) -> Optional[dict]:
    """对单只股票复现选股条件；通过返回指标 dict，否则 None。"""
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


def _batch_evaluate(cands: List[Tuple[str, str, Optional[str]]], t_date: str) -> List[dict]:
    results: List[dict] = []
    if not cands:
        return results
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futs = {
            pool.submit(_evaluate, code, name, industry, t_date): code
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
    """计算最新交易日的打板选股。返回 (选股日, 结果)；无法确定交易日返回 None。"""
    sessions = _last_two_sessions()
    if not sessions:
        return None
    t1_date, t_date = sessions

    pool = _get_candidate_pool(t1_date)
    if pool is None:
        logger.info("打板：涨停池不可用，回退全市场扫描")
        pool = _full_market_pool()

    matches = _batch_evaluate(pool, t_date)
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


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@router.get("/candidates", response_model=List[BoardPick])
async def get_board_candidates(date: Optional[str] = None):
    """
    打板每日选股。

    - 不传 date：取最新交易日。数据库里已有当天快照直接返回，没有才计算并落库。
    - 传 date=YYYY-MM-DD：只读历史快照，不触发扫描。
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


@router.post("/sync", response_model=List[BoardPick])
async def sync_board_candidates():
    """强制重新计算最新交易日并覆盖当天快照。"""
    computed = _compute_board_picks()
    if computed is None:
        return []
    trade_date, picks = computed
    board_store.save_snapshot(trade_date, picks)
    return picks


@router.get("/dates", response_model=List[str])
async def get_board_dates():
    """最近 10 个有快照的交易日（倒序）。"""
    return board_store.list_dates(limit=board_store.KEEP_DAYS)

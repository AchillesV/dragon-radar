"""
趋势信号路由 —— 早期启动形态识别

规则（v0.4，见 issue 讨论定稿版）：
  阶段① 放量日 D：近 10 个交易日内，某天成交量 ≥ 该日之前 5 日均量 × 2.5
  阶段② 持续放量：D 之后每一天成交量都 ≥ 放量前 5 日基准均量 × 1.5（不打回原形）
  阶段③ 横盘：3日/5日/10日 中任意一个窗口，累计涨跌幅 ∈ [-10%, 10%]

数据来源：全部改为腾讯 K 线（个股日线），阶段①②③在同一次抓取里一起算，
不再依赖东方财富/百度的资金流接口 —— 那两个数据源在生产环境反复验证都拿不到
数据（详见 issue 历史评论），且这次简化后阶段③不再需要资金净流入数据，正好
不再依赖它们。

股票池来自沪深京交易所官方股票列表（akshare stock_info_a_code_name，非
东财 push2 接口），逐只股票抓取腾讯 K 线校验三阶段条件；剔除创业板/ST后
全市场约 5000+ 只，用 20 并发抓取，冷启动一次计算约 1 分钟量级，用较长
TTL 缓存结果。
"""
import datetime
import logging
import time
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from fastapi import APIRouter

import trend_store
from models import TrendStock
from routers.screening import _fetch_hist_tencent

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# 规则参数（锁定值，来自设计文档 v0.3 / v0.4）
# ---------------------------------------------------------------------------
BREAKOUT_BASELINE_DAYS = 5
BREAKOUT_MULTIPLIER = 2.5
SUSTAIN_MULTIPLIER = 1.5
LOOKBACK_TRADING_DAYS = 10
RANGE_WINDOWS = (3, 5, 10)
CHANGE_PCT_MIN, CHANGE_PCT_MAX = -10.0, 10.0

# ---------------------------------------------------------------------------
# ST / 创业板 剔除（与 anomaly.py / screening.py 保持一致的过滤规则）
# ---------------------------------------------------------------------------


def _is_qualified(code: str, name: str) -> bool:
    if code.startswith("300") or code.startswith("301"):
        return False
    if "ST" in name.upper():
        return False
    return True


# ---------------------------------------------------------------------------
# 全市场股票池（沪深京交易所官方列表，非东财 push2，24小时缓存）
# ---------------------------------------------------------------------------

_UNIVERSE_CACHE: Optional[Tuple[float, List[Tuple[str, str]]]] = None
_UNIVERSE_TTL = 24 * 3600


def _get_universe() -> List[Tuple[str, str]]:
    """返回 [(code, name), ...]，已剔除创业板/ST"""
    global _UNIVERSE_CACHE
    now = time.time()
    if _UNIVERSE_CACHE and now - _UNIVERSE_CACHE[0] < _UNIVERSE_TTL:
        return _UNIVERSE_CACHE[1]

    import akshare as ak

    df = None
    for attempt in range(3):
        try:
            df = ak.stock_info_a_code_name()
            break
        except Exception as e:
            logger.warning(f"获取全市场股票列表第{attempt + 1}次失败: {e}")
            time.sleep(2 * (attempt + 1))
    if df is None:
        return _UNIVERSE_CACHE[1] if _UNIVERSE_CACHE else []

    universe = [
        (str(row["code"]), str(row["name"]))
        for _, row in df.iterrows()
        if _is_qualified(str(row["code"]), str(row["name"]))
    ]
    _UNIVERSE_CACHE = (now, universe)
    logger.info(f"全市场股票池刷新: {len(universe)} 只（已剔除创业板/ST）")
    return universe


# ---------------------------------------------------------------------------
# 阶段①②③：单只股票的历史行情一次抓取，同时校验放量+持续放量+横盘
# ---------------------------------------------------------------------------


def _detect_breakout(volumes: List[float], dates: List[str]) -> Optional[dict]:
    """
    在最近 LOOKBACK_TRADING_DAYS 个交易日内寻找放量日 D：
      某天成交量 >= 该日之前 BREAKOUT_BASELINE_DAYS 日均量 * BREAKOUT_MULTIPLIER
    且 D 之后每一天成交量都 >= 放量前基准均量 * SUSTAIN_MULTIPLIER。
    返回最早满足条件的 D（含基准均量/放量日成交量/日期），否则 None。
    """
    n = len(volumes)
    if n < BREAKOUT_BASELINE_DAYS + 1:
        return None

    search_start = max(BREAKOUT_BASELINE_DAYS, n - LOOKBACK_TRADING_DAYS)

    for i in range(search_start, n):
        baseline = volumes[i - BREAKOUT_BASELINE_DAYS:i]
        baseline_avg = sum(baseline) / len(baseline)
        if baseline_avg <= 0 or volumes[i] < baseline_avg * BREAKOUT_MULTIPLIER:
            continue

        tail = volumes[i + 1:]
        if all(v >= baseline_avg * SUSTAIN_MULTIPLIER for v in tail):
            return {
                "d_date": str(dates[i]),
                "d_volume": float(volumes[i]),
                "baseline_avg": round(baseline_avg, 0),
            }
    return None


def _check_range(closes: List[float]) -> Optional[dict]:
    """
    3/5/10 日窗口，任意一个窗口的累计涨跌幅在 [-10%, 10%] 之间即通过。
    累计涨跌幅 = (窗口最后一天收盘价 / 窗口第一天前一交易日收盘价 - 1) * 100
    """
    n = len(closes)
    for w in RANGE_WINDOWS:
        if n < w + 1:
            continue
        start_close = closes[-w - 1]
        end_close = closes[-1]
        if start_close <= 0:
            continue
        change_pct = round((end_close / start_close - 1) * 100, 2)
        if CHANGE_PCT_MIN <= change_pct <= CHANGE_PCT_MAX:
            return {"window": f"{w}日", "change_pct": change_pct}
    return None


def _check_one(code: str, name: str) -> Optional[dict]:
    df = _fetch_hist_tencent(code, days=25)
    if df is None or df.empty:
        return None

    volumes = df["成交量"].tolist()
    closes = df["收盘"].tolist()
    dates = df["日期"].tolist()

    breakout = _detect_breakout(volumes, dates)
    if not breakout:
        return None
    range_match = _check_range(closes)
    if not range_match:
        return None

    # 计算每日涨跌额和涨跌幅
    daily_change = None
    daily_change_pct = 0.0
    if len(closes) >= 2:
        daily_change = round(closes[-1] - closes[-2], 2)
        if closes[-2] > 0:
            daily_change_pct = round((closes[-1] / closes[-2] - 1) * 100, 2)

    return {
        "code": code,
        "name": name,
        "price": closes[-1] if closes else None,
        "change": daily_change,
        "change_pct": daily_change_pct,
        "breakout": breakout,
        "range_window": range_match["window"],
        "range_change_pct": range_match["change_pct"],
    }


def _batch_check(universe: List[Tuple[str, str]]) -> List[dict]:
    results: List[dict] = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = {pool.submit(_check_one, code, name): code for code, name in universe}
        for fut in as_completed(futs):
            try:
                match = fut.result()
                if match:
                    results.append(match)
            except Exception as e:
                logger.debug(f"trend check error {futs[fut]}: {e}")
    return results


# ---------------------------------------------------------------------------
# 交易日判定 + 结果落库 —— 同一交易日内不重复全市场扫描，
# 只有当天（最新交易日）在数据库里没有快照时才触发一次全市场扫描。
# ---------------------------------------------------------------------------

_SESSION_DATE_SAMPLE_CODE = "600000"  # 取样股票，仅用于判定最新交易日日期


def _get_session_date() -> str:
    """最新交易日日期（YYYY-MM-DD），取样一只流动性好的股票的最后一根K线日期。"""
    df = _fetch_hist_tencent(_SESSION_DATE_SAMPLE_CODE, days=5)
    if df is not None and not df.empty:
        return str(df["日期"].iloc[-1])
    return datetime.date.today().strftime("%Y-%m-%d")


def _apply_hit_count(stocks: List[TrendStock], session_date: str) -> List[TrendStock]:
    """标注统计周期内入选次数，并按入选次数从高到低排序。"""
    if not stocks:
        return stocks
    hit_map = trend_store.compute_hit_counts(session_date, lookback=LOOKBACK_TRADING_DAYS)
    for s in stocks:
        s.hit_count = hit_map.get(s.code, 1)
    stocks.sort(key=lambda s: s.hit_count, reverse=True)
    return stocks


def _compute_trend_stocks() -> List[TrendStock]:
    universe = _get_universe()
    if not universe:
        return []

    logger.info(f"开始全市场趋势扫描，股票池 {len(universe)} 只...")
    t0 = time.time()
    matches = _batch_check(universe)
    logger.info(f"趋势扫描完成，用时 {time.time() - t0:.1f}s，命中 {len(matches)} 只")

    result: List[TrendStock] = []
    for m in matches:
        breakout = m["breakout"]
        result.append(TrendStock(
            code=m["code"],
            name=m["name"],
            price=m.get("price"),
            change=m.get("change"),
            change_pct=m["change_pct"],
            breakout_date=breakout["d_date"],
            breakout_volume=breakout["d_volume"],
            baseline_avg_volume=breakout["baseline_avg"],
            range_window=m["range_window"],
            range_change_pct=m["range_change_pct"],
            description=(
                f"{breakout['d_date']} 放量启动，{m['range_window']}累计涨跌幅 "
                f"{m['range_change_pct']}%（横盘）"
            ),
        ))

    result.sort(key=lambda s: s.breakout_date, reverse=True)
    return result


@router.get("/candidates", response_model=List[TrendStock])
async def get_trend_candidates(date: Optional[str] = None):
    """
    获取「趋势」信号候选股（放量启动 + 持续放量 + 横盘）

    - 不传 date：查最新交易日。数据库里已有当天快照就直接返回，
      没有才触发一次全市场扫描并落库（避免每次刷新都重新扫全市场）。
    - 传 date=YYYY-MM-DD：只从数据库里查历史快照，不触发扫描。
    - 无论哪种情况，都会标注「统计周期内入选次数」，并按入选次数从高到低排序。
    """
    if date:
        stocks = trend_store.load_snapshot(date)
        return _apply_hit_count(stocks, date)

    session_date = _get_session_date()
    stocks = trend_store.load_snapshot(session_date)
    if stocks:
        return _apply_hit_count(stocks, session_date)

    try:
        stocks = _compute_trend_stocks()
        if stocks:
            trend_store.save_snapshot(session_date, stocks)
        return _apply_hit_count(stocks, session_date)
    except Exception as e:
        logger.warning(f"趋势信号计算失败: {e}")
        return []


@router.post("/sync", response_model=List[TrendStock])
async def sync_trend_candidates():
    """
    手动触发一次当天全市场重新扫描，并用最新结果覆盖数据库中当天已有的快照。

    与 `/candidates` 的懒加载策略不同（当天已有数据就直接复用），此接口
    无论当天是否已有快照都会重新扫描一次，供用户在盘中/盘后手动刷新最新数据。
    """
    session_date = _get_session_date()
    stocks = _compute_trend_stocks()
    trend_store.save_snapshot(session_date, stocks)  # save_snapshot 内部先删后插，天然覆盖当天旧数据
    return _apply_hit_count(stocks, session_date)


@router.get("/dates", response_model=List[str])
async def get_trend_dates():
    """最近有快照的交易日列表（倒序），供前端「近10天」下拉筛选使用。"""
    return trend_store.list_dates(limit=LOOKBACK_TRADING_DAYS)

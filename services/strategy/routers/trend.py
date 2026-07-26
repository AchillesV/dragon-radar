"""
趋势信号路由 —— 早期启动形态识别

规则（见 issue 讨论定稿版）：
  阶段① 放量日 D：近 10 个交易日内，某天成交量 ≥ 该日之前 5 日均量 × 2.5
  阶段② 持续放量：D 之后每一天成交量都 ≥ 放量前 5 日基准均量 × 1.5（不打回原形）
  阶段③ 横盘 + 资金净流入：3日/5日/10日 中任意一个窗口，同时满足
        涨跌幅 ∈ [-10%, 10%] 且 主力净流入 > 0（两者必须来自同一个窗口）

数据来源：
  阶段①② —— 复用 screening.py 里已有的腾讯 K 线抓取（个股日线，1小时缓存）
  阶段③ —— 东方财富全市场资金流排名批量接口（一次调用覆盖全市场，非逐只股票请求）

阶段③ batch 结果天然覆盖全市场且开销很小，所以先算阶段③、过滤出候选子集，
再对这个子集做阶段①②的逐只股票历史抓取，避免对全市场 5000+ 只股票都做历史请求。
"""
import logging
import time
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from fastapi import APIRouter

from models import TrendStock
from routers.screening import _fetch_hist_tencent

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# 规则参数（锁定值，来自设计文档 v0.3）
# ---------------------------------------------------------------------------
BREAKOUT_BASELINE_DAYS = 5
BREAKOUT_MULTIPLIER = 2.5
SUSTAIN_MULTIPLIER = 1.5
LOOKBACK_TRADING_DAYS = 10
FUND_FLOW_WINDOWS = ("3日", "5日", "10日")
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
# 阶段③：全市场资金流/涨跌幅排名（批量接口，短 TTL 缓存）
# ---------------------------------------------------------------------------

_FUND_FLOW_CACHE: Dict[str, Tuple[float, pd.DataFrame]] = {}
_FUND_FLOW_TTL = 600  # 10分钟；该接口本身就是滚动 3/5/10 日的累计值，不需要高频刷新


def _fetch_fund_flow_rank(indicator: str) -> Optional[pd.DataFrame]:
    now = time.time()
    cached = _FUND_FLOW_CACHE.get(indicator)
    if cached and now - cached[0] < _FUND_FLOW_TTL:
        return cached[1]

    import akshare as ak

    for attempt in range(3):
        try:
            df = ak.stock_individual_fund_flow_rank(indicator=indicator)
            _FUND_FLOW_CACHE[indicator] = (now, df)
            return df
        except Exception as e:
            logger.warning(f"stock_individual_fund_flow_rank({indicator}) 第{attempt + 1}次失败: {e}")
            time.sleep(1.5 * (attempt + 1))
    return None


def _build_phase3_candidates() -> Dict[str, dict]:
    """
    拉取 3/5/10 日资金流排名，构建 code -> {window, change_pct, main_inflow, name} 的候选集合。
    只保留至少命中一个窗口（涨跌幅达标 且 主力净流入>0）的股票。
    """
    candidates: Dict[str, dict] = {}

    for window in FUND_FLOW_WINDOWS:
        df = _fetch_fund_flow_rank(window)
        if df is None or df.empty:
            logger.warning(f"资金流排名 {window} 获取失败，跳过该窗口")
            continue

        change_col = f"{window}涨跌幅"
        inflow_col = f"{window}主力净流入-净额"
        if change_col not in df.columns or inflow_col not in df.columns:
            continue

        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            name = str(row.get("名称", ""))
            if not code or code in candidates:
                continue
            if not _is_qualified(code, name):
                continue

            change_pct = pd.to_numeric(row.get(change_col), errors="coerce")
            main_inflow_yuan = pd.to_numeric(row.get(inflow_col), errors="coerce")
            if pd.isna(change_pct) or pd.isna(main_inflow_yuan):
                continue

            if CHANGE_PCT_MIN <= change_pct <= CHANGE_PCT_MAX and main_inflow_yuan > 0:
                candidates[code] = {
                    "name": name,
                    "price": pd.to_numeric(row.get("最新价"), errors="coerce"),
                    "window": window,
                    "change_pct": round(float(change_pct), 2),
                    "main_inflow": round(float(main_inflow_yuan) / 1e8, 2),  # 元 -> 亿元
                }

    return candidates


# ---------------------------------------------------------------------------
# 阶段①②：放量日检测 + 持续放量校验（逐只股票历史行情）
# ---------------------------------------------------------------------------


def _detect_breakout(df: pd.DataFrame) -> Optional[dict]:
    """
    在最近 LOOKBACK_TRADING_DAYS 个交易日内寻找放量日 D：
      某天成交量 >= 该日之前 BREAKOUT_BASELINE_DAYS 日均量 * BREAKOUT_MULTIPLIER
    且 D 之后每一天成交量都 >= 放量前基准均量 * SUSTAIN_MULTIPLIER。
    返回最早满足条件的 D（含基准均量/放量日成交量/日期），否则 None。
    """
    if df is None or len(df) < BREAKOUT_BASELINE_DAYS + 1:
        return None

    n = len(df)
    volumes = df["成交量"].tolist()
    dates = df["日期"].tolist()

    search_start = max(BREAKOUT_BASELINE_DAYS, n - LOOKBACK_TRADING_DAYS)

    for i in range(search_start, n):
        baseline = volumes[i - BREAKOUT_BASELINE_DAYS:i]
        baseline_avg = sum(baseline) / len(baseline)
        if baseline_avg <= 0 or volumes[i] < baseline_avg * BREAKOUT_MULTIPLIER:
            continue

        # D 之后（不含 D 当天）每一天都不能跌破基准均量的 SUSTAIN_MULTIPLIER 倍
        tail = volumes[i + 1:]
        if all(v >= baseline_avg * SUSTAIN_MULTIPLIER for v in tail):
            return {
                "d_date": str(dates[i]),
                "d_volume": float(volumes[i]),
                "baseline_avg": round(baseline_avg, 0),
            }
    return None


def _check_one(code: str) -> Optional[dict]:
    # days=25 与 screening.py 的默认值保持一致，复用同一份 1 小时内存缓存
    # （_HIST_CACHE 按 code 缓存，不区分 days，值必须一致才不会互相截断）
    df = _fetch_hist_tencent(code, days=25)
    if df is None or df.empty:
        return None
    return _detect_breakout(df)


def _batch_detect_breakout(codes: List[str]) -> Dict[str, dict]:
    results: Dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = {pool.submit(_check_one, code): code for code in codes}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                match = fut.result()
                if match:
                    results[code] = match
            except Exception as e:
                logger.debug(f"breakout detection error {code}: {e}")
    return results


# ---------------------------------------------------------------------------
# 组合结果（10分钟缓存，避免同一交易日内重复触发全量计算）
# ---------------------------------------------------------------------------

_RESULT_CACHE: Optional[Tuple[float, List[TrendStock]]] = None
_RESULT_TTL = 600


def _compute_trend_stocks() -> List[TrendStock]:
    phase3 = _build_phase3_candidates()
    if not phase3:
        return []

    logger.info(f"阶段③命中 {len(phase3)} 只候选股，开始阶段①②历史行情校验...")
    t0 = time.time()
    breakouts = _batch_detect_breakout(list(phase3.keys()))
    logger.info(f"阶段①②校验完成，用时 {time.time() - t0:.1f}s，最终命中 {len(breakouts)} 只")

    result: List[TrendStock] = []
    for code, breakout in breakouts.items():
        p3 = phase3[code]
        result.append(TrendStock(
            code=code,
            name=p3["name"],
            price=p3.get("price"),
            change_pct=p3["change_pct"],
            breakout_date=breakout["d_date"],
            breakout_volume=breakout["d_volume"],
            baseline_avg_volume=breakout["baseline_avg"],
            fund_flow_window=p3["window"],
            fund_flow_change_pct=p3["change_pct"],
            fund_flow_main_inflow=p3["main_inflow"],
            description=(
                f"{breakout['d_date']} 放量启动（{p3['window']}资金净流入 "
                f"{p3['main_inflow']}亿，{p3['window']}涨跌幅 {p3['change_pct']}%）"
            ),
        ))

    result.sort(key=lambda s: s.fund_flow_main_inflow, reverse=True)
    return result


@router.get("/candidates", response_model=List[TrendStock])
async def get_trend_candidates():
    """
    获取「趋势」信号候选股（放量启动 + 持续放量 + 横盘资金净流入）
    结果按当前交易日缓存 10 分钟，避免重复触发全市场扫描。
    """
    global _RESULT_CACHE
    now = time.time()
    if _RESULT_CACHE and now - _RESULT_CACHE[0] < _RESULT_TTL:
        return _RESULT_CACHE[1]

    try:
        result = _compute_trend_stocks()
        _RESULT_CACHE = (now, result)
        return result
    except Exception as e:
        logger.warning(f"趋势信号计算失败: {e}")
        if _RESULT_CACHE:
            return _RESULT_CACHE[1]
        return []

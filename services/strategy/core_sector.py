"""
「核心」板块数据层 —— 同花顺行业资金流 / 行业成交额 / 行业指数历史。

东财 push2 系接口（板块行情、板块成分、板块资金流）在部分网络环境会被断开连接，
因此这里统一使用同花顺数据源：
  - ak.stock_fund_flow_industry(symbol="即时" | "5日排行" | "10日排行")
  - ak.stock_board_industry_summary_ths()          今日成交额、上涨/下跌家数
  - ak.stock_board_industry_index_ths(symbol=行业)  行业指数日线成交额（算放量）

「所属行业」来自东财涨停池，名称会被截断（如「汽车零部」），
_resolve_industry() 依次用 别名表 → 去后缀 → 前缀包含 → 模糊匹配 对齐到同花顺行业名。
"""
from __future__ import annotations

import difflib
import time
from datetime import datetime, timedelta
from statistics import mean
from typing import Dict, List, Optional

import pandas as pd

_CACHE: Dict[str, dict] = {}

_FUND_TTL = 600      # 行业资金流 10 分钟
_SUMMARY_TTL = 300   # 行业一览 5 分钟
_HIST_TTL = 1800     # 行业指数历史 30 分钟

# 东财涨停池「所属行业」→ 同花顺行业 的别名（无法靠截断/包含自动对齐的少数情况）
_ALIAS = {
    "一般零售": "零售",
    "航运港口": "港口航运",
    "铁路公路": "公路铁路运输",
    "旅游及景": "旅游及酒店",
    "航天装备": "军工装备",
    "饮料乳品": "饮料制造",
    "焦炭Ⅱ": "煤炭开采加工",
    "休闲食品": "食品加工制造",   # 近似：同花顺无三级细分行业
}


def _num(v) -> Optional[float]:
    """把 akshare 返回的字符串/百分比/空值统一成 float。"""
    try:
        if v is None:
            return None
        s = str(v).replace("%", "").replace(",", "").strip()
        if s in ("", "-", "--", "nan", "NaN", "None"):
            return None
        return float(s)
    except Exception:
        return None


def _cache(key: str, ttl: int, loader):
    """带 TTL 的进程内缓存；加载失败只缓存 60 秒，避免瞬时故障锁死一个周期。"""
    item = _CACHE.get(key)
    if item and time.time() - item["ts"] < ttl:
        return item["val"]
    try:
        val = loader()
    except Exception:
        _CACHE[key] = {"val": None, "ts": time.time() - ttl + min(ttl, 60)}
        return None
    _CACHE[key] = {"val": val, "ts": time.time()}
    return val


# ---------------------------------------------------------------------------
# 同花顺数据抓取
# ---------------------------------------------------------------------------

def _load_fund_flow(period: str) -> Optional[pd.DataFrame]:
    import akshare as ak

    df = ak.stock_fund_flow_industry(symbol=period)
    if df is None or df.empty or "行业" not in df.columns:
        return None
    df["行业"] = df["行业"].astype(str)
    return df


def _fund_map(period: str) -> Dict[str, dict]:
    """行业 → {净额(亿), 阶段涨跌幅(%)}"""
    df = _cache(f"fund:{period}", _FUND_TTL, lambda: _load_fund_flow(period))
    if df is None:
        return {}
    change_col = "行业-涨跌幅" if "行业-涨跌幅" in df.columns else "阶段涨跌幅"
    out: Dict[str, dict] = {}
    for _, row in df.iterrows():
        out[str(row["行业"])] = {
            "net": _num(row.get("净额")),
            "change": _num(row.get(change_col)),
        }
    return out


def _load_summary() -> Optional[pd.DataFrame]:
    import akshare as ak

    df = ak.stock_board_industry_summary_ths()
    if df is None or df.empty or "板块" not in df.columns:
        return None
    df["板块"] = df["板块"].astype(str)
    return df


def _summary_map() -> Dict[str, dict]:
    """行业 → {涨跌幅, 成交额(亿), 上涨家数, 下跌家数}"""
    df = _cache("industry_summary", _SUMMARY_TTL, _load_summary)
    if df is None:
        return {}
    out: Dict[str, dict] = {}
    for _, row in df.iterrows():
        out[str(row["板块"])] = {
            "change": _num(row.get("涨跌幅")),
            "amount": _num(row.get("总成交额")),
            "rise": _num(row.get("上涨家数")),
            "fall": _num(row.get("下跌家数")),
        }
    return out


def _volume_ratio(name: str) -> Optional[float]:
    """近 3 日成交额均值 / 前 20 日成交额均值。"""
    today = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=45)).strftime("%Y%m%d")

    def load():
        import akshare as ak

        df = ak.stock_board_industry_index_ths(
            symbol=name, start_date=start, end_date=today
        )
        if df is None or df.empty or "成交额" not in df.columns:
            return None
        return [x for x in (_num(v) for v in df["成交额"].tolist()) if x and x > 0]

    amounts = _cache(f"hist:{name}:{today}", _HIST_TTL, load)
    if not amounts or len(amounts) < 8:
        return None
    recent = amounts[-3:]
    base = amounts[-23:-3] or amounts[:-3]
    if not base or mean(base) <= 0:
        return None
    return round(mean(recent) / mean(base), 2)


# ---------------------------------------------------------------------------
# 行业名对齐（东财涨停池 → 同花顺行业）
# ---------------------------------------------------------------------------

def _resolve_industry(name: str, names: List[str]) -> Optional[str]:
    if name in names:
        return name
    alias = _ALIAS.get(name)
    if alias and alias in names:
        return alias

    base = name.replace("Ⅱ", "").replace("Ⅲ", "").replace("Ⅰ", "")
    if base in names:
        return base

    candidates = [n for n in names if n.startswith(base) or base.startswith(n)]
    if len(candidates) == 1:
        return candidates[0]

    close = difflib.get_close_matches(base, names, n=1, cutoff=0.8)
    return close[0] if close else None


def enrich_sector(name: str) -> dict:
    """把一个东财行业名补充成板块级指标（拿不到的统一返回 None）。"""
    summary = _summary_map()
    matched = _resolve_industry(name, sorted(summary.keys())) if summary else None

    result = {
        "matched_name": matched,
        "main_net_today": None,
        "main_net_5d": None,
        "main_net_10d": None,
        "amount_today": None,
        "rise_ratio": None,
        "volume_ratio": None,
    }
    if not matched:
        return result

    for period, field in (("即时", "main_net_today"), ("5日排行", "main_net_5d"), ("10日排行", "main_net_10d")):
        fund = _fund_map(period).get(matched)
        if fund:
            result[field] = fund["net"]

    s = summary.get(matched)
    if s:
        result["amount_today"] = s["amount"]
        rise, fall = s["rise"], s["fall"]
        if rise is not None and fall is not None and (rise + fall) > 0:
            result["rise_ratio"] = round(rise / (rise + fall), 3)

    result["volume_ratio"] = _volume_ratio(matched)
    return result

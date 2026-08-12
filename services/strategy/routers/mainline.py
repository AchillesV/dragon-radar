"""
「主线」板块路由 —— 主力核心票列表（issue WHT-9 重新定义）

WHT-9 变更：
  1. 删除子板块资金流模块（原 /sectors 接口 + 东财资金流抓取逻辑），子板块
     分类概念一并移除。
  2. 核心票筛选不再限定候选池：全市场（已剔除创业板 300/301、科创板 688、ST）
     逐只验证 2026-04-01~2026-06-30 累计涨幅 >=80%，命中的全部收录。见
     mainline_universe.py docstring 与 scripts/compute_core_stocks_fullmarket.py。

核心票列表当日价格/涨跌幅走腾讯实时行情（批量一次请求，30 秒缓存）。
"""
import time
from typing import Dict, List, Optional

import requests
from fastapi import APIRouter

from mainline_universe import CORE_STOCKS
from models import MainlineStock

router = APIRouter()

_TENCENT_HEADERS = {"User-Agent": "Mozilla/5.0"}

# ---------------------------------------------------------------------------
# 核心票当日行情（腾讯实时行情，批量一次请求）
# ---------------------------------------------------------------------------
_QUOTE_CACHE: Optional[Dict] = None
_QUOTE_TTL = 30


def _fetch_quotes(codes: List[str]) -> Dict[str, dict]:
    global _QUOTE_CACHE
    now = time.time()
    if _QUOTE_CACHE and now - _QUOTE_CACHE["ts"] < _QUOTE_TTL:
        return _QUOTE_CACHE["data"]

    prefixed = []
    for c in codes:
        prefix = "sh" if c.startswith(("6", "9")) else ("bj" if c.startswith("8") else "sz")
        prefixed.append(f"{prefix}{c}")

    result: Dict[str, dict] = {}
    try:
        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        r = requests.get(url, headers=_TENCENT_HEADERS, timeout=10)
        data = r.content.decode("gbk", errors="ignore")
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            vals = line.split('"')[1].split("~")
            if len(vals) < 38:
                continue
            code = key[2:]
            result[code] = {
                "price": float(vals[3]) if vals[3] else 0.0,
                "change_pct": float(vals[32]) if vals[32] else 0.0,
                "amount": float(vals[37]) * 10000 if vals[37] else 0.0,  # 万元 -> 元
            }
    except Exception:
        pass

    _QUOTE_CACHE = {"data": result, "ts": now}
    return result


@router.get("/stocks", response_model=List[MainlineStock])
async def get_mainline_stocks():
    """
    主力核心票列表（2026-04-01~2026-06-30 累计涨幅 >=80%，全市场逐只验证）。
    按今日涨跌幅从高到低排序。
    """
    codes = list(CORE_STOCKS.keys())
    quotes = _fetch_quotes(codes)

    result: List[MainlineStock] = []
    for code, info in CORE_STOCKS.items():
        q = quotes.get(code, {})
        result.append(MainlineStock(
            code=code,
            name=info["name"],
            price=q.get("price"),
            change_pct=q.get("change_pct", 0.0),
            amount=q.get("amount"),
            period_gain_pct=info["period_gain_pct"],
            period_start=info["period_start"],
            period_end=info["period_end"],
        ))
    result.sort(key=lambda x: x.change_pct, reverse=True)
    return result

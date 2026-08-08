"""
「主线」板块路由 —— 科技主线子板块资金流 + 核心票列表

数据构成（对应 issue WHT-8 用户补充说明）：
  1. 子板块分类 + 核心票静态数据：mainline_universe.py（16 个子板块，人工按产业链
     环节整理，核心票已用腾讯 K 线真实历史行情验证「2026-04-01~2026-06-30 涨幅
     翻倍」，见该文件 docstring 与 scripts/compute_core_stocks.py）。
  2. 子板块当日主力资金净流入额 = 该子板块分类池内所有股票当日主力净流入额相加
     （用户要求）。主力净流入走 akshare 个股资金流向接口（东财），与 trend.py
     文档里记录的历史结论一致——该数据源在生产环境反复验证过并不稳定，因此这里
     对每只股票的抓取做了独立超时+异常隔离，单只失败不影响其它股票；若整批全部
     失败（数据源整体不可用），子板块净流入退化为 0 并标记 matched_count=0，不
     在没有真实数据时编造流入额。
  3. 核心票列表当日价格/涨跌幅走腾讯实时行情（不受上面资金流数据源问题影响）。

不剔除创业板（300/301开头）——与 anomaly.py/screening.py/trend.py 的过滤规则
不同，是有意为之：科技主线核心票天然大量分布在创业板/科创板（如模拟芯片龙头
圣邦股份 300661），沿用异动监控那套过滤规则会错误剔除真实的主线龙头。仍剔除
ST，避免风险股混入"主线核心票"列表。
"""
import logging
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import requests
from fastapi import APIRouter, Query

from mainline_universe import CORE_STOCKS, STOCK_SUBSECTOR_MAP, SUBSECTORS
from models import MainlineSectorFlow, MainlineStock

logger = logging.getLogger(__name__)
router = APIRouter()

_TENCENT_HEADERS = {"User-Agent": "Mozilla/5.0"}

# ---------------------------------------------------------------------------
# 当日主力净流入额（东财个股资金流向，60秒缓存，单只股票失败不影响其它）
# ---------------------------------------------------------------------------
_FLOW_CACHE: Optional[Dict] = None
_FLOW_TTL = 60


def _market_of(code: str) -> str:
    if code.startswith(("6", "9")):
        return "sh"
    if code.startswith(("8", "4")):
        return "bj"
    return "sz"


_FUND_FLOW_URL = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
_MARKET_SECID = {"sh": 1, "sz": 0, "bj": 0}


def _fetch_one_fund_flow(code: str) -> Optional[float]:
    """
    单只股票当日主力净流入额（元）；失败/超时返回 None，不抛异常。

    没有直接调用 akshare 的 stock_individual_fund_flow —— 该封装内部
    requests.get 不带 timeout，一旦这个数据源被限流/连接被重置（详见本文件
    模块 docstring），单个请求可能长时间挂起，拖慢整批 20 并发抓取。这里
    复刻同样的东财接口调用但显式加 timeout，故障时能在有限时间内快速跳过。
    """
    import time as _time

    try:
        params = {
            "lmt": "0", "klt": "101",
            "secid": f"{_MARKET_SECID[_market_of(code)]}.{code}",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "_": int(_time.time() * 1000),
        }
        r = requests.get(_FUND_FLOW_URL, params=params, headers=_TENCENT_HEADERS, timeout=6)
        klines = r.json()["data"]["klines"]
        if not klines:
            return None
        # 每行: 日期,主力净流入-净额,小单净流入-净额,中单净流入-净额,大单净流入-净额,超大单净流入-净额,...
        return float(klines[-1].split(",")[1])
    except Exception as e:
        logger.debug(f"mainline fund flow error {code}: {e}")
        return None


def _get_all_fund_flow() -> Dict[str, float]:
    """全量分类股票池的当日主力净流入额，60秒缓存。"""
    global _FLOW_CACHE
    now = time.time()
    if _FLOW_CACHE and now - _FLOW_CACHE["ts"] < _FLOW_TTL:
        return _FLOW_CACHE["data"]

    all_codes = sorted({code for stocks in STOCK_SUBSECTOR_MAP.values() for code, _ in stocks})
    result: Dict[str, float] = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = {pool.submit(_fetch_one_fund_flow, code): code for code in all_codes}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                v = fut.result()
                if v is not None:
                    result[code] = v
            except Exception:
                pass

    _FLOW_CACHE = {"data": result, "ts": now}
    logger.info(f"主线资金流刷新: {len(result)}/{len(all_codes)} 只取到真实数据")
    return result


@router.get("/sectors", response_model=List[MainlineSectorFlow])
async def get_mainline_sectors():
    """
    16 个科技主线子板块，按当日主力资金净流入额加总从高到低排序（用于柱状图）。
    净流入额 = 该子板块分类池内所有股票当日主力净流入额相加。
    """
    flow_map = _get_all_fund_flow()
    result: List[MainlineSectorFlow] = []
    for s in SUBSECTORS:
        stocks = STOCK_SUBSECTOR_MAP.get(s.id, [])
        matched = [flow_map[code] for code, _ in stocks if code in flow_map]
        result.append(MainlineSectorFlow(
            id=s.id,
            name=s.name,
            group=s.group,
            hot=s.hot,
            net_inflow=sum(matched),
            stock_count=len(stocks),
            matched_count=len(matched),
        ))
    result.sort(key=lambda x: x.net_inflow, reverse=True)
    return result


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
    except Exception as e:
        logger.warning(f"主线核心票实时行情获取失败: {e}")

    _QUOTE_CACHE = {"data": result, "ts": now}
    return result


@router.get("/stocks", response_model=List[MainlineStock])
async def get_mainline_stocks(subsector: Optional[str] = Query(None)):
    """
    科技主线核心票列表（2026-04-01~2026-06-30 累计涨幅翻倍，已用真实历史行情验证）。
    可选 subsector 过滤，列表按今日涨跌幅从高到低排序。
    """
    codes = list(CORE_STOCKS.keys())
    quotes = _fetch_quotes(codes)

    result: List[MainlineStock] = []
    for code, info in CORE_STOCKS.items():
        if subsector and subsector not in info["subsectors"]:
            continue
        q = quotes.get(code, {})
        result.append(MainlineStock(
            code=code,
            name=info["name"],
            subsectors=info["subsectors"],
            price=q.get("price"),
            change_pct=q.get("change_pct", 0.0),
            amount=q.get("amount"),
            period_gain_pct=info["period_gain_pct"],
            period_start=info["period_start"],
            period_end=info["period_end"],
        ))
    result.sort(key=lambda x: x.change_pct, reverse=True)
    return result

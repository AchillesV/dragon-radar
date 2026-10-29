"""
「核心」路由 —— 热门板块内的首板（一板）候选。

规则（标准档）：
  1. 板块预筛（涨停池）：涨停家数 >= 3（或 >=2 且上涨占比 >= 65%），且
     板块最高连板 = 全市场最高板（>=3），或连板 >=2 的家数 >= 2
  2. 板块确认（同花顺）：5 日资金净额 > 0 且今日净额 > 0；
     近 3 日板块成交额均值 / 前 20 日均值 >= 1.3
  3. 个股：连板数 == 1，剔除创业板 300/301、科创板 688、ST

板块级数据拿不到时（同花顺网络异常 / 行业名无法对齐），该条件视为「未知」放行，
并在 data_quality=partial、板块 reasons 中标注，不伪造 mock 数据。
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter

import core_sector
from models import CoreResult, CoreSector, CoreStock
from routers.trend import _get_session_date

logger = logging.getLogger(__name__)
router = APIRouter()

# 标准档阈值
MIN_LIMIT_UP = 3
MIN_RISE_RATIO = 0.65
MIN_VOLUME_RATIO = 1.3
MAX_CANDIDATES = 12   # 参与板块级精算的候选上限（控制同花顺请求数）
MAX_SECTORS = 8       # 最终展示的热门板块上限

_CACHE: Dict[str, dict] = {"key": "", "ts": 0.0, "val": None}
_CACHE_TTL = 60


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def _num(v) -> Optional[float]:
    try:
        if v is None:
            return None
        s = str(v).replace(",", "").strip()
        if s in ("", "-", "--", "nan", "NaN", "None"):
            return None
        return float(s)
    except Exception:
        return None


def _fmt_time(v) -> Optional[str]:
    s = str(v).strip()
    if len(s) == 6 and s.isdigit():
        return f"{s[:2]}:{s[2:4]}:{s[4:]}"
    return s or None


def _is_qualified(code: str, name: str) -> bool:
    """与 trend 模块对齐：剔除创业板 300/301、科创板 688、ST。"""
    if code.startswith(("300", "301", "688")):
        return False
    if "ST" in name.upper():
        return False
    return True


def _load_zt_pool(session_date: str) -> Tuple[Optional[pd.DataFrame], str]:
    """取最近一个可用的涨停池（盘前/节假日自动向前回退）。"""
    import akshare as ak

    base = datetime.strptime(session_date, "%Y-%m-%d").date()
    for i in range(0, 6):
        day = base - timedelta(days=i)
        try:
            df = ak.stock_zt_pool_em(date=day.strftime("%Y%m%d"))
        except Exception as e:
            logger.warning(f"涨停池 {day} 获取失败: {e}")
            df = None
        if df is not None and not df.empty:
            return df, day.strftime("%Y-%m-%d")
    return None, session_date


def _collect_rows(df: pd.DataFrame) -> List[dict]:
    rows: List[dict] = []
    for _, r in df.iterrows():
        code = str(r.get("代码", "")).strip().zfill(6)
        name = str(r.get("名称", "")).strip()
        if not code or not _is_qualified(code, name):
            continue
        rows.append({
            "code": code,
            "name": name,
            "sector": str(r.get("所属行业", "其他")).strip() or "其他",
            "price": _num(r.get("最新价")),
            "change_pct": _num(r.get("涨跌幅")) or 0.0,
            "amount": _num(r.get("成交额")),
            "seal_amount": _num(r.get("封板资金")),
            "turnover_rate": _num(r.get("换手率")),
            "first_limit_time": _fmt_time(r.get("首次封板时间")),
            "break_count": int(_num(r.get("炸板次数")) or 0),
            "limit_stat": str(r.get("涨停统计")) if r.get("涨停统计") else None,
            "board": int(_num(r.get("连板数")) or 1),
        })
    return rows


def _aggregate(rows: List[dict]) -> Dict[str, dict]:
    stats: Dict[str, dict] = {}
    for r in rows:
        s = stats.setdefault(r["sector"], {
            "count": 0, "max_board": 0, "multi": 0, "one": 0,
        })
        s["count"] += 1
        s["max_board"] = max(s["max_board"], r["board"])
        if r["board"] >= 2:
            s["multi"] += 1
        if r["board"] == 1:
            s["one"] += 1
    return stats


def _score(st: dict, ext: dict, market_max: int) -> float:
    vol = ext.get("volume_ratio")
    net5 = ext.get("main_net_5d")
    vol_score = 35.0 * min(1.0, (vol or 1.0) / 2.0)
    fund_score = 30.0 * min(1.0, max(net5 or 0.0, 0.0) / 50.0)
    breadth_score = 20.0 * min(1.0, st["count"] / 6.0)
    if st["max_board"] >= market_max and st["max_board"] >= 2:
        height_score = 15.0
    else:
        height_score = min(15.0, 5.0 * st["multi"])
    return round(vol_score + fund_score + breadth_score + height_score, 1)


def _reasons(st: dict, ext: dict, market_max: int) -> List[str]:
    reasons: List[str] = [f"涨停{st['count']}家"]
    if station := ext.get("main_net_5d"):
        reasons.append(f"5日净额{station:+.1f}亿")
    elif station == 0:
        reasons.append("5日净额0.0亿")
    else:
        reasons.append("资金数据缺失")

    if (vol := ext.get("volume_ratio")) is not None:
        reasons.append(f"放量{vol}x")
    else:
        reasons.append("放量数据缺失")

    if (rr := ext.get("rise_ratio")) is not None:
        reasons.append(f"上涨占比{rr * 100:.0f}%")
    if st["max_board"] >= market_max and market_max >= 2:
        reasons.append(f"全市场最高板{market_max}板")
    elif st["multi"]:
        reasons.append(f"{st['multi']}家连板")
    return reasons


def _build_sector(name: str, st: dict, ext: dict, market_max: int, reasons: List[str]) -> CoreSector:
    return CoreSector(
        name=name,
        matched_name=ext.get("matched_name"),
        limit_up_count=st["count"],
        max_board=st["max_board"],
        multi_board_count=st["multi"],
        one_board_count=st["one"],
        main_net_today=ext.get("main_net_today"),
        main_net_5d=ext.get("main_net_5d"),
        main_net_10d=ext.get("main_net_10d"),
        amount_today=ext.get("amount_today"),
        volume_ratio=ext.get("volume_ratio"),
        rise_ratio=ext.get("rise_ratio"),
        score=_score(st, ext, market_max),
        reasons=reasons,
    )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def _compute() -> CoreResult:
    session = _get_session_date()
    df, trade_date = _load_zt_pool(session)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if df is None:
        logger.warning("核心：涨停池不可用，返回空结果")
        return CoreResult(date=trade_date, generated_at=now, data_quality="partial")

    rows = _collect_rows(df)
    market_max = max((r["board"] for r in rows), default=0)
    stats = _aggregate(rows)

    # 预筛：高度（扩散度需要外部上涨家数，放到 enrich 之后再判定）
    candidates: List[str] = []
    for name, st in sorted(stats.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
        if len(candidates) >= MAX_CANDIDATES:
            break
        if st["count"] < 2:
            continue
        height_ok = (st["max_board"] >= market_max and market_max >= 2) or st["multi"] >= 2
        if not height_ok:
            continue
        candidates.append(name)

    sectors: List[CoreSector] = []
    watchlist: List[CoreSector] = []
    partial = False
    for name in candidates:
        st = stats[name]
        ext = core_sector.enrich_sector(name)

        # 扩散度：涨停 >=3 家；或 >=2 家且板块上涨占比 >= 65%
        rr = ext.get("rise_ratio")
        if st["count"] >= MIN_LIMIT_UP:
            breadth_ok = True
        else:
            breadth_ok = rr is not None and rr >= MIN_RISE_RATIO
        if not breadth_ok:
            continue

        net5 = ext.get("main_net_5d")
        net_today = ext.get("main_net_today")
        vol = ext.get("volume_ratio")

        # 观察池：扩散 + 高度已达标，但资金 / 放量未达标
        fails: List[str] = []
        if net5 is not None and (net5 <= 0 or (net_today is not None and net_today <= 0)):
            fails.append(f"5日净额{net5:+.1f}亿" if net5 <= 0 else f"今日净额{net_today:+.1f}亿")
        if vol is not None and vol < MIN_VOLUME_RATIO:
            fails.append(f"放量{vol}x")
        if fails:
            watchlist.append(_build_sector(name, st, ext, market_max, fails))
            continue

        if ext.get("matched_name") is None or vol is None or net5 is None:
            partial = True

        sectors.append(_build_sector(name, st, ext, market_max, _reasons(st, ext, market_max)))

    sectors.sort(key=lambda s: s.score, reverse=True)
    sectors = sectors[:MAX_SECTORS]
    watchlist.sort(key=lambda s: s.score, reverse=True)
    watchlist = watchlist[:MAX_SECTORS]
    hot = {s.name: s.score for s in sectors}

    stocks: List[CoreStock] = []
    for r in rows:
        if r["board"] != 1 or r["sector"] not in hot:
            continue
        stocks.append(CoreStock(
            code=r["code"],
            name=r["name"],
            sector=r["sector"],
            price=r["price"],
            change_pct=r["change_pct"],
            amount=r["amount"],
            seal_amount=r["seal_amount"],
            turnover_rate=r["turnover_rate"],
            first_limit_time=r["first_limit_time"],
            break_count=r["break_count"],
            limit_stat=r["limit_stat"],
            sector_score=hot[r["sector"]],
        ))
    stocks.sort(key=lambda s: (s.sector_score, s.seal_amount or 0), reverse=True)

    return CoreResult(
        date=trade_date,
        generated_at=now,
        market_max_board=market_max,
        data_quality="partial" if partial else "full",
        sectors=sectors,
        watchlist=watchlist,
        stocks=stocks,
    )


@router.get("", response_model=CoreResult)
async def get_core() -> CoreResult:
    """热门板块 + 板块内首板候选（60 秒缓存）。"""
    now = time.time()
    if _CACHE["val"] is not None and now - _CACHE["ts"] < _CACHE_TTL:
        return _CACHE["val"]

    result = _compute()
    _CACHE.update({"key": "core", "ts": now, "val": result})
    return result

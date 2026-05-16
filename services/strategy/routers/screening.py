"""
选股筛选路由 — 特征驱动候选股发现
"""
import json
import logging
import time
import datetime
from typing import List, Optional, Dict, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd

from fastapi import APIRouter, Query
from pydantic import BaseModel
from models import CandidateStock, FeatureInfo, FilterRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# 历史行情缓存（Tencent K-line API，内存 TTL 1小时）
# ---------------------------------------------------------------------------
_HIST_CACHE: Dict[str, Tuple[float, pd.DataFrame]] = {}   # code → (ts, df)
_HIST_TTL = 3600
_TENCENT_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
# 需要历史行情的特征集合
HIST_FEATURE_IDS = {"multi_limit_15d", "vol_surge_3d", "five_day_rally"}


def _fetch_hist_tencent(code: str, days: int = 25) -> Optional[pd.DataFrame]:
    """
    从腾讯 K 线接口拉取个股日线数据，带 1 小时内存缓存。
    返回 DataFrame，列：日期, 开盘, 收盘, 最高, 最低, 成交量, 涨跌幅
    """
    now = time.time()
    cached = _HIST_CACHE.get(code)
    if cached and now - cached[0] < _HIST_TTL:
        return cached[1]

    prefix = "sh" if code.startswith("6") or code.startswith("9") else "sz"
    full = f"{prefix}{code}"
    end_d = datetime.date.today().strftime("%Y-%m-%d")
    start_d = (datetime.date.today() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
    url = (f"https://ifzq.gtimg.cn/appstock/app/kline/kline"
           f"?p=1&param={full},day,{start_d},{end_d},{days}&_var=m_{full}_day")
    try:
        r = requests.get(url, headers=_TENCENT_HEADERS, timeout=8)
        text = r.text
        data = json.loads(text[text.index("=") + 1:])
        rows = data["data"][full]["day"]
        df = pd.DataFrame(rows, columns=["日期", "开盘", "收盘", "最高", "最低", "成交量"])
        for col in ["开盘", "收盘", "最高", "最低", "成交量"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["涨跌幅"] = df["收盘"].pct_change() * 100
        df = df.dropna(subset=["涨跌幅"]).reset_index(drop=True)
        df = df.tail(days)
        _HIST_CACHE[code] = (now, df)
        return df
    except Exception as e:
        logger.debug(f"Tencent hist error {code}: {e}")
        return None


def _check_hist_features(code: str, requested: Set[str]) -> Set[str]:
    """对单只股票计算历史特征，只计算 requested 中的特征。"""
    feats: Set[str] = set()
    if not (requested & HIST_FEATURE_IDS):
        return feats

    df = _fetch_hist_tencent(code, days=25)
    if df is None or df.empty:
        return feats

    # ── 15天内有3个及以上涨停板 ──────────────────────────────────────────────
    if "multi_limit_15d" in requested and len(df) >= 5:
        recent15 = df.tail(15)
        # 主板≥9.8%, 创业板/科创板≥19.8%; 统一用 9.8% 做阈值（20%板也满足）
        n = int((recent15["涨跌幅"] >= 9.8).sum())
        if n >= 3:
            feats.add("multi_limit_15d")

    # ── 近3天至少一次3倍放量上涨 ────────────────────────────────────────────
    if "vol_surge_3d" in requested and len(df) >= 8:
        recent3 = df.tail(3)
        baseline = df.tail(8).head(5)          # 近3天之前的5个交易日作为基准
        avg_vol = baseline["成交量"].mean()
        if avg_vol > 0:
            for _, row in recent3.iterrows():
                if row["涨跌幅"] > 0 and row["成交量"] >= avg_vol * 3:
                    feats.add("vol_surge_3d")
                    break

    # ── 5天内连续上涨 ────────────────────────────────────────────────────────
    if "five_day_rally" in requested and len(df) >= 5:
        recent5 = df.tail(5)
        if (recent5["涨跌幅"] > 0).all():
            feats.add("five_day_rally")

    return feats


def _batch_hist_features(codes: List[str], requested: Set[str]) -> Dict[str, Set[str]]:
    """并行为多只股票计算历史特征，最多 20 并发。"""
    results: Dict[str, Set[str]] = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = {pool.submit(_check_hist_features, c, requested): c for c in codes}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                feats = fut.result()
                if feats:
                    results[code] = feats
            except Exception as e:
                logger.debug(f"hist feature error {code}: {e}")
    return results

# ---------------------------------------------------------------------------
# Mock 候选股数据
# ---------------------------------------------------------------------------

_ALL_CANDIDATES = [
    CandidateStock(code="300750", name="宁德时代", change_pct=9.87, amount=45.6, turnover=12.3,
                   industry="电池", market_cap=8120.0, pe=32.5,
                   matched_features=["volume_surge", "lianban_upgrade", "recent_limit", "fund_inflow", "lianban"],
                   score=9.2),
    CandidateStock(code="002371", name="北方华创", change_pct=10.01, amount=23.4, turnover=8.7,
                   industry="半导体", market_cap=1250.0, pe=45.2,
                   matched_features=["volume_surge", "lianban_upgrade", "weak_to_strong", "recent_limit", "lianban"],
                   score=9.0),
    CandidateStock(code="688041", name="海光信息", change_pct=9.95, amount=18.7, turnover=6.5,
                   industry="芯片", market_cap=560.0, pe=89.3,
                   matched_features=["lianban_upgrade", "recent_limit", "lianban", "fund_inflow"],
                   score=8.7),
    CandidateStock(code="300015", name="爱尔眼科", change_pct=5.23, amount=8.7, turnover=11.5,
                   industry="医疗服务", market_cap=1870.0, pe=35.6,
                   matched_features=["high_turnover", "weak_to_strong", "volume_surge"],
                   score=7.6),
    CandidateStock(code="002594", name="比亚迪", change_pct=2.87, amount=78.9, turnover=1.8,
                   industry="新能源汽车", market_cap=73200.0, pe=28.4,
                   matched_features=["fund_inflow"],
                   score=6.8),
    CandidateStock(code="601288", name="农业银行", change_pct=0.54, amount=34.5, turnover=0.4,
                   industry="银行", market_cap=137800.0, pe=5.2,
                   matched_features=["fund_inflow"],
                   score=5.2),
    CandidateStock(code="600519", name="贵州茅台", change_pct=-1.87, amount=89.1, turnover=0.3,
                   industry="白酒", market_cap=207000.0, pe=28.5,
                   matched_features=[],
                   score=4.1),
    CandidateStock(code="000858", name="五粮液", change_pct=-2.34, amount=43.2, turnover=0.9,
                   industry="白酒", market_cap=53900.0, pe=18.7,
                   matched_features=[],
                   score=3.2),
]

_CANDIDATE_MAP = {s.code: s for s in _ALL_CANDIDATES}


ALL_FEATURES = [
    FeatureInfo(id="volume_surge",     name="量能异动",    description="成交量≥5日均量×2.5且当日上涨", is_default=True),
    FeatureInfo(id="high_turnover",    name="高换手",      description="换手率≥10%", is_default=True),
    FeatureInfo(id="weak_to_strong",   name="弱转强",      description="早盘跌>1%，收盘涨>3%", is_default=True),
    FeatureInfo(id="reverse_limit",    name="反包涨停",    description="当日从跌停到涨停", is_default=False),
    FeatureInfo(id="rebound_limit",    name="炸板回封",    description="炸板后重新封板", is_default=False),
    FeatureInfo(id="eod_rush",         name="尾盘冲量",    description="尾盘30分钟放量创新高", is_default=False),
    FeatureInfo(id="gap_down_fade",    name="高开低走",    description="高开3%以上，收盘跌>2%", is_default=False),
    FeatureInfo(id="quiet_limit",      name="静默涨停",    description="涨停且换手率<3%", is_default=False),
    FeatureInfo(id="lianban_upgrade",  name="连板升级",    description="连板数≥2且今日涨停", is_default=True),
    FeatureInfo(id="dragon_separate",  name="龙头分化",    description="板块内龙头涨幅>板块均值×2", is_default=False),
    FeatureInfo(id="sector_resonance", name="板块共振",    description="同日≥3概念板块各有≥3只涨停", is_default=False),
    FeatureInfo(id="recent_limit",     name="近期涨停",    description="近5日内曾出现涨停", is_default=True),
    FeatureInfo(id="fund_inflow",      name="资金流入",    description="主力净流入>1亿", is_default=True),
    FeatureInfo(id="lianban",          name="连板股",      description="当日处于连板状态", is_default=True),
    # ── 历史行情特征（腾讯日线接口）─────────────────────────────────────────
    FeatureInfo(id="multi_limit_15d",  name="多涨停",      description="15天内涨停板≥3次",         is_default=True),
    FeatureInfo(id="vol_surge_3d",     name="近期放量",    description="近3天至少一次3倍放量上涨",  is_default=True),
    FeatureInfo(id="five_day_rally",   name="5天连涨",     description="最近5个交易日连续上涨",     is_default=False),
]


def _row_to_base(row) -> dict:
    """Convert a pool DataFrame row to a base stock dict."""
    amount_yuan = float(row.get("成交额", 0) or 0)
    mktcap_yuan = float(row.get("总市值", 0) or 0)
    circ_yuan    = float(row.get("流通市值", 0) or 0)
    pe_raw       = row.get("动态市盈率")
    return {
        "code":          str(row["代码"]),
        "name":          str(row["名称"]),
        "change_pct":    float(row.get("涨跌幅", 0) or 0),
        "price":         float(row.get("最新价", 0) or 0),
        "amount":        round(amount_yuan / 1e8, 2),
        "turnover":      float(row.get("换手率", 0) or 0),
        "industry":      str(row.get("所属行业", "") or ""),
        "market_cap":    round(mktcap_yuan / 1e8, 2) if mktcap_yuan > 0 else None,
        "circ_market_cap": round(circ_yuan / 1e8, 2) if circ_yuan > 0 else None,
        "pe":            float(pe_raw) if pe_raw and str(pe_raw) not in ("nan", "None", "--") else None,
    }


def _fetch_real_candidates(feature_ids: List[str]) -> Optional[List[CandidateStock]]:
    """
    从 akshare 涨停池 / 强势股池 / 昨日涨停池中拉取实时数据，
    按请求的特征取并集，返回 CandidateStock 列表。

    特征 → 数据源映射：
      lianban / lianban_upgrade  → zt_pool_em   连板数 >= 2
      quiet_limit                → zt_pool_em   换手率 < 3
      rebound_limit              → zt_pool_em   炸板次数 >= 1
      high_turnover              → 任意池        换手率 >= 10
      volume_surge               → strong_em    量比 >= 2.5
      weak_to_strong             → strong_em    是否新高=="是" 或 昨涨停&今涨
      recent_limit               → 全部三个池
      fund_inflow                → 任意池        成交额 >= 10 亿（代理指标）
      reverse_limit              → zt_pool_em   炸板次数 >= 2（近似）
    """
    import akshare as ak

    today = datetime.date.today().strftime("%Y%m%d")
    ids_set: Set[str] = set(feature_ids)

    # code → { base fields, features: Set[str], lianban_count: int }
    registry: Dict[str, dict] = {}

    def register(row, features: Set[str], lianban: int = 1):
        base = _row_to_base(row)
        code = base["code"]
        if code not in registry:
            registry[code] = {**base, "features": set(), "lianban_count": lianban}
        registry[code]["features"].update(features)
        if lianban > registry[code].get("lianban_count", 1):
            registry[code]["lianban_count"] = lianban

    # ── 1. 涨停池 ─────────────────────────────────────────────────────────────
    try:
        zt = ak.stock_zt_pool_em(date=today)
        for _, row in zt.iterrows():
            lianban = int(row.get("连板数", 1) or 1)
            turnover = float(row.get("换手率", 0) or 0)
            zhaban   = int(row.get("炸板次数", 0) or 0)
            amount   = float(row.get("成交额", 0) or 0) / 1e8

            feats: Set[str] = {"recent_limit"}
            if lianban >= 2:
                feats.update({"lianban", "lianban_upgrade"})
            if turnover < 3:
                feats.add("quiet_limit")
            if turnover >= 10:
                feats.add("high_turnover")
            if zhaban >= 1:
                feats.add("rebound_limit")
            if zhaban >= 2:
                feats.add("reverse_limit")      # 多次炸板后回封 ≈ 反包
            if amount >= 10:
                feats.add("fund_inflow")

            register(row, feats, lianban)
    except Exception as e:
        logger.warning(f"stock_zt_pool_em error: {e}")

    # ── 2. 强势股池（含量比、是否新高）────────────────────────────────────────
    try:
        strong = ak.stock_zt_pool_strong_em(date=today)
        for _, row in strong.iterrows():
            turnover   = float(row.get("换手率", 0) or 0)
            vol_ratio  = float(row.get("量比", 1) or 1)
            is_new_high = str(row.get("是否新高", "否")).strip() == "是"
            amount      = float(row.get("成交额", 0) or 0) / 1e8

            feats: Set[str] = {"recent_limit"}
            if vol_ratio >= 2.5:
                feats.add("volume_surge")
            if turnover >= 10:
                feats.add("high_turnover")
            if is_new_high:
                feats.add("weak_to_strong")
            if amount >= 10:
                feats.add("fund_inflow")

            # 涨停统计 field like "3/5" → 近期有过涨停
            register(row, feats, lianban=1)
    except Exception as e:
        logger.warning(f"stock_zt_pool_strong_em error: {e}")

    # ── 3. 昨日涨停池（今日表现是否延续）────────────────────────────────────
    try:
        prev = ak.stock_zt_pool_previous_em(date=today)
        for _, row in prev.iterrows():
            turnover    = float(row.get("换手率", 0) or 0)
            change_pct  = float(row.get("涨跌幅", 0) or 0)
            yesterday_n = int(row.get("昨日连板数", 1) or 1)
            amount      = float(row.get("成交额", 0) or 0) / 1e8

            feats: Set[str] = {"recent_limit"}
            if change_pct > 0:
                feats.add("weak_to_strong")   # 昨涨停今继续上涨 = 弱转强延续
            if turnover >= 10:
                feats.add("high_turnover")
            if amount >= 10:
                feats.add("fund_inflow")

            register(row, feats, lianban=yesterday_n)
    except Exception as e:
        logger.warning(f"stock_zt_pool_previous_em error: {e}")

    if not registry:
        return None

    # ── 4. 历史特征（腾讯日线，并行拉取）────────────────────────────────────
    hist_requested = set(feature_ids) & HIST_FEATURE_IDS
    if hist_requested:
        all_codes = list(registry.keys())
        logger.info(f"Fetching hist features {hist_requested} for {len(all_codes)} stocks...")
        t0 = time.time()
        hist_map = _batch_hist_features(all_codes, hist_requested)
        logger.info(f"Hist fetch done in {time.time()-t0:.1f}s, matched {len(hist_map)} stocks")
        for code, feats in hist_map.items():
            if code in registry:
                registry[code]["features"].update(feats)

    _FEATURE_DESC = {
        "lianban":          "连板中",
        "lianban_upgrade":  "连板升级",
        "quiet_limit":      "缩量涨停，筹码锁定",
        "high_turnover":    "换手活跃",
        "rebound_limit":    "炸板回封，主力意志坚定",
        "reverse_limit":    "多次反复，最终封板",
        "volume_surge":     "放量异动，量比超2.5倍",
        "weak_to_strong":   "弱转强/创新高",
        "recent_limit":     "近期涨停",
        "fund_inflow":      "大额资金净流入",
        "multi_limit_15d":  "15天内≥3次涨停",
        "vol_surge_3d":     "近3天3倍放量上涨",
        "five_day_rally":   "5天连续上涨",
    }

    # ── 筛选：至少匹配一个请求的特征 ──────────────────────────────────────────
    result: List[CandidateStock] = []
    for code, data in registry.items():
        matched = [f for f in feature_ids if f in data["features"]]
        if not matched:
            continue

        lianban = data.get("lianban_count", 1)
        # 历史特征命中额外加权
        hist_bonus = sum(0.5 for f in matched if f in HIST_FEATURE_IDS)
        score = round(min(9.9, 5.0 + len(matched) * 0.7 + lianban * 0.4 + hist_bonus), 1)
        desc_parts = [_FEATURE_DESC.get(f, f) for f in matched]
        if lianban > 1:
            desc_parts.append(f"第{lianban}板")

        result.append(CandidateStock(
            code=code,
            name=data["name"],
            change_pct=data["change_pct"],
            price=data.get("price"),
            amount=data["amount"],
            turnover=data["turnover"],
            industry=data.get("industry") or None,
            market_cap=data.get("market_cap"),
            circ_market_cap=data.get("circ_market_cap"),
            pe=data.get("pe"),
            lianban_count=lianban if lianban > 1 else None,
            matched_features=matched,
            description="；".join(desc_parts),
            score=score,
        ))

    result.sort(key=lambda x: (x.score or 0), reverse=True)
    return result or None


@router.get("/candidates", response_model=List[CandidateStock])
async def get_candidates(
    feature_ids: str = Query("recent_limit,lianban", description="逗号分隔的特征ID列表"),
):
    """
    获取候选股票列表（按多个 feature_id 取并集，实时数据）
    """
    ids = [f.strip() for f in feature_ids.split(",") if f.strip()]
    if not ids:
        ids = ["recent_limit"]

    try:
        result = _fetch_real_candidates(ids)
        if result:
            return result
    except Exception as e:
        logger.warning(f"Real candidate fetch failed: {e}")

    # Fallback：静态 mock 数据
    result = []
    seen: set = set()
    for fid in ids:
        for stock in _ALL_CANDIDATES:
            if fid in stock.matched_features and stock.code not in seen:
                seen.add(stock.code)
                matched = [f for f in ids if f in stock.matched_features]
                result.append(CandidateStock(
                    **stock.model_dump(exclude={"matched_features", "lianban_count", "price", "circ_market_cap"}),
                    matched_features=matched,
                ))
    result.sort(key=lambda x: x.score or 0, reverse=True)
    return result


@router.post("/filter", response_model=List[CandidateStock])
async def filter_stocks(body: FilterRequest):
    """
    在给定股票代码列表上应用过滤条件
    """
    codes = body.codes or []
    filters = body.filters or {}

    # 获取候选股基础数据
    stocks = [_CANDIDATE_MAP.get(code) for code in codes if code in _CANDIDATE_MAP]
    # 对于不在 mock 中的代码，生成基础数据
    for code in codes:
        if code not in _CANDIDATE_MAP:
            stocks.append(CandidateStock(
                code=code, name=f"股票{code}", change_pct=0.0, amount=5.0, turnover=1.0,
                matched_features=[], score=5.0,
            ))

    stocks = [s for s in stocks if s is not None]

    # 应用过滤条件
    def passes_filter(s: CandidateStock) -> bool:
        if not filters:
            return True

        # 板块/行业过滤
        if "sector" in filters and filters["sector"]:
            if s.industry != filters["sector"]:
                return False

        # 市值过滤（单位：亿）
        if "marketCap" in filters and filters["marketCap"]:
            mc = filters["marketCap"]
            if isinstance(mc, dict):
                if "min" in mc and s.market_cap is not None and s.market_cap < mc["min"]:
                    return False
                if "max" in mc and s.market_cap is not None and s.market_cap > mc["max"]:
                    return False
            elif isinstance(mc, (int, float)):
                if s.market_cap is not None and s.market_cap > mc:
                    return False

        # 涨跌幅过滤
        if "changePct" in filters and filters["changePct"]:
            cp = filters["changePct"]
            if isinstance(cp, dict):
                if "min" in cp and s.change_pct < cp["min"]:
                    return False
                if "max" in cp and s.change_pct > cp["max"]:
                    return False

        # 换手率过滤
        if "turnoverRate" in filters and filters["turnoverRate"]:
            tr = filters["turnoverRate"]
            if isinstance(tr, dict):
                if "min" in tr and s.turnover < tr["min"]:
                    return False
                if "max" in tr and s.turnover > tr["max"]:
                    return False

        # PE 过滤
        if "pe" in filters and filters["pe"]:
            pe_filter = filters["pe"]
            if isinstance(pe_filter, dict):
                if "min" in pe_filter and s.pe is not None and s.pe < pe_filter["min"]:
                    return False
                if "max" in pe_filter and s.pe is not None and s.pe > pe_filter["max"]:
                    return False

        return True

    filtered = [s for s in stocks if passes_filter(s)]
    filtered.sort(key=lambda x: x.score or 0, reverse=True)
    return filtered


@router.get("/features", response_model=List[FeatureInfo])
async def get_features():
    """获取所有内置特征列表"""
    return ALL_FEATURES

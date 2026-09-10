"""
「趋势 → 分析」个股评分（V2 Phase 2）

在 Phase 1（候选池 → 板块热度/资金/扩散度）之上，给每只趋势候选股加三个维度，
把候选池从 200~300 只压缩到 50 只重点股：

  * Smart Money Score（资金行为，0~100）
      15% 放量启动质量 + 10% 启动后量能保持 + 15% 个股相对强度 + 15% 板块共振
      + 10% 资金（板块级代理）+ 10% 回调资金稳定性 + 10% 再次放量突破
      + 5% 新高/突破 + 10% 资金信号新鲜度
  * RS（个股相对强度，0~100）：个股 5 日涨幅相对 沪深300 / 中证1000 / 所属行业 / 所属概念 的超额
  * Freshness（资金信号新鲜度，0~100）：100 × e^(-0.12 × 放量启动至今交易日数)

数据来源：全部基于腾讯行情（个股/指数 K 线 + 板块级指标），无 Key、无需逐股资金流。
口径说明（已在 issue 中与仓库所有者确认）：
  * 资金维度不接逐股净流入，用「所属行业板块的主力净额/成交额」做代理；
  * 概念侧只覆盖 Phase 1 选出的热度 TOP 概念（全量概念成分股会触发限流）。
"""
import datetime
import json
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import requests

from routers.screening import _fetch_hist_tencent

logger = logging.getLogger(__name__)

# 重点股数量：候选池 → 50 只
SHORTLIST = 50
CORE_COUNT = 20

# 市场环境模块（设计文档模块 1）尚未实现，先用中性 50 分占位，保留文档权重不变
MARKET_ENV_NEUTRAL = 50.0

# 指数代码（腾讯行情）
INDEX_HS300 = "sh000300"
INDEX_ZZ1000 = "sh000852"

_INDEX_URL = "https://ifzq.gtimg.cn/appstock/app/kline/kline"
_INDEX_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
_INDEX_CACHE: Dict[str, Tuple[float, Optional[float]]] = {}
_INDEX_TTL = 3600


def _to_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _norm(value: Optional[float], lo: float, hi: float) -> float:
    """线性归一化到 0~100。"""
    if value is None or hi <= lo:
        return 0.0
    return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100.0))


def _fetch_index_ret5(code_full: str, days: int = 25) -> Optional[float]:
    """指数近 5 个交易日累计涨跌幅（%），带 1 小时缓存。"""
    now = time.time()
    cached = _INDEX_CACHE.get(code_full)
    if cached and now - cached[0] < _INDEX_TTL:
        return cached[1]

    end_d = datetime.date.today().strftime("%Y-%m-%d")
    start_d = (datetime.date.today() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
    ret: Optional[float] = None
    try:
        r = requests.get(_INDEX_URL, headers=_INDEX_HEADERS, timeout=8, params={
            "p": "1", "param": f"{code_full},day,{start_d},{end_d},{days}", "_var": "x",
        })
        text = r.text
        data = json.loads(text[text.index("=") + 1:])
        day = (data.get("data") or {}).get(code_full, {}).get("day") or []
        closes = [_to_float(x[2]) for x in day]
        if len(closes) >= 6 and closes[-6] > 0:
            ret = round((closes[-1] / closes[-6] - 1) * 100, 2)
    except Exception as e:
        logger.debug(f"指数 K 线获取失败 {code_full}: {e}")

    _INDEX_CACHE[code_full] = (now, ret)
    return ret


def _score_one(
    entry: dict,
    df,
    industry: Optional[dict],
    concepts: List[dict],
    idx_ret: Dict[str, Optional[float]],
    meta: Optional[dict] = None,
) -> Optional[dict]:
    """对单只候选股计算 SmartMoney / RS / Freshness。df 列：日期,开盘,收盘,最高,最低,成交量,涨跌幅。"""
    if df is None or len(df) < 8:
        return None

    dates = [str(x) for x in df["日期"].tolist()]
    closes = [_to_float(x) for x in df["收盘"].tolist()]
    highs = [_to_float(x) for x in df["最高"].tolist()]
    volumes = [_to_float(x) for x in df["成交量"].tolist()]
    pcts = [_to_float(x) for x in df["涨跌幅"].tolist()]

    # 放量启动日 D 的下标（取最近一次出现）
    d_date = str(entry.get("breakout_date") or "")
    try:
        d_idx = dates.index(d_date)
    except ValueError:
        d_idx = -1

    b_avg = _to_float(entry.get("baseline_avg_volume")) or (
        sum(volumes[:5]) / 5 if len(volumes) >= 5 else 0.0
    )
    v_d = _to_float(entry.get("breakout_volume")) or (volumes[d_idx] if d_idx >= 0 else 0.0)

    # ---- A. 放量启动质量：D 日相对基准的量比 + D 日涨幅 ----
    ratio = (v_d / b_avg) if b_avg > 0 else 0.0
    pct_d = pcts[d_idx] if d_idx >= 0 else 0.0
    breakout_quality = 0.6 * _norm(ratio, 2.5, 6.0) + 0.4 * _norm(pct_d, 0.0, 9.0)

    # ---- B. 启动后量能保持：D 之后均量 / 基准均量 ----
    after = volumes[d_idx + 1:] if d_idx >= 0 else volumes[-5:]
    sustain_ratio = (sum(after) / len(after) / b_avg) if (after and b_avg > 0) else 0.0
    volume_sustain = _norm(sustain_ratio, 1.2, 3.0)

    # ---- C. 个股相对强度：5 日涨幅 vs 沪深300 / 中证1000 / 行业 / 概念 ----
    ret5 = ((closes[-1] / closes[-6] - 1) * 100) if len(closes) >= 6 and closes[-6] > 0 else 0.0
    excess: List[float] = []
    if idx_ret.get(INDEX_HS300) is not None:
        excess.append(ret5 - idx_ret[INDEX_HS300])
    if idx_ret.get(INDEX_ZZ1000) is not None:
        excess.append(ret5 - idx_ret[INDEX_ZZ1000])
    if industry and industry.get("change5_pct") is not None:
        excess.append(ret5 - industry["change5_pct"])
    if concepts:
        best_con = max(concepts, key=lambda c: c.get("score") or 0)
        if best_con.get("change5_pct") is not None:
            excess.append(ret5 - best_con["change5_pct"])
    rs_raw = sum(excess) / len(excess) if excess else 0.0
    # 超额收益映射：0 → 50 分，±15 个百分点 → 100/0
    rs_score = _norm(rs_raw, -15.0, 15.0)

    # ---- C2. 板块内相对强度：个股 5 日涨幅相对所属行业的超额 ----
    sector_rel = (ret5 - industry["change5_pct"]
                  if industry and industry.get("change5_pct") is not None else rs_raw)
    sector_rel_score = _norm(sector_rel, -8.0, 15.0)

    # ---- D. 板块共振：所属行业/概念板块热度取最高 ----
    sector_scores = [b.get("score") for b in ([industry] if industry else []) + list(concepts or [])
                     if b and b.get("score") is not None]
    sector_resonance = max(sector_scores) if sector_scores else 50.0

    # ---- E. 资金（板块级代理）：所属行业板块主力净额/成交额 ----
    inflow_pct = industry.get("net_inflow_pct") if industry else None
    net_inflow_comp = _norm(inflow_pct, -5.0, 8.0) if inflow_pct is not None else 50.0

    # ---- F. 回调资金稳定性：回调日是否缩量（缩量占比） ----
    window_start = max(0, len(pcts) - 10)
    pull_cnt = shrink_cnt = 0
    for i in range(window_start + 1, len(pcts)):
        if pcts[i] < 0:
            pull_cnt += 1
            if volumes[i] < volumes[i - 1]:
                shrink_cnt += 1
    resilience = (shrink_cnt / pull_cnt * 100) if pull_cnt else 70.0

    # ---- G. 再次放量突破：最近一日放量 且 收在近 10 日高点之上 ----
    restart = 0.0
    if len(volumes) >= 6:
        prev_avg = sum(volumes[-6:-1]) / 5
        last_ratio = volumes[-1] / prev_avg if prev_avg > 0 else 0.0
        recent_high = max(highs[-11:-1]) if len(highs) >= 11 else max(highs[:-1])
        if last_ratio >= 1.3 and pcts[-1] > 0:
            restart = 0.7 * _norm(last_ratio, 1.3, 3.0) + 0.3 * (100.0 if closes[-1] >= recent_high else 40.0)
        elif last_ratio >= 1.1 and pcts[-1] > 0:
            restart = 0.5 * _norm(last_ratio, 1.1, 2.0)

    # ---- H. 新高 / 突破：当前价在近 20 日高低区间的位置 ----
    hi = max(highs[-20:]) if len(highs) >= 20 else max(highs)
    lo = min(closes[-20:]) if len(closes) >= 20 else min(closes)
    new_high = _norm(closes[-1], lo, hi) if hi > lo else 50.0

    # ---- I. 资金信号新鲜度 ----
    days_since = ((len(dates) - 1) - d_idx) if d_idx >= 0 else 5
    freshness = 100.0 * math.exp(-0.12 * max(0, days_since))

    # ---- J. 成交额 / 换手（来自板块成分股指标；缺失时中性） ----
    m = meta or {}
    turnover = _to_float(m.get("turnover"))          # 成交额（万元）
    amount_comp = _norm(math.log10(turnover), 3.5, 5.7) if turnover > 0 else 50.0
    hsl = _to_float(m.get("turnover_rate"))          # 换手率 %
    attention = _norm(hsl, 0.5, 8.0) if hsl > 0 else 50.0

    # ---- K. 趋势完整性：入选次数越稳定、横盘越居中越好 ----
    range_chg = _to_float(entry.get("range_change_pct"))
    hit_count = _to_float(entry.get("hit_count"), 1.0)
    trend_integrity = (
        0.5 * _norm(hit_count, 1.0, 3.0)
        + 0.5 * (100.0 - _norm(abs(range_chg), 0.0, 12.0))
    )

    smart_money = (
        0.15 * breakout_quality
        + 0.10 * volume_sustain
        + 0.15 * rs_score
        + 0.15 * sector_resonance
        + 0.10 * net_inflow_comp
        + 0.10 * resilience
        + 0.10 * restart
        + 0.05 * new_high
        + 0.10 * freshness
    )

    # ---- 核心股评分 CoreScore（设计文档模块 5） ----
    core_score = (
        0.20 * sector_rel_score
        + 0.15 * net_inflow_comp
        + 0.15 * amount_comp
        + 0.10 * trend_integrity
        + 0.10 * breakout_quality
        + 0.10 * resilience
        + 0.10 * sector_resonance
        + 0.05 * freshness
        + 0.05 * attention
    )

    # ---- 综合评分 FinalScore（设计文档 §21；市场环境模块未实现，用中性 50 占位） ----
    score = (
        25 * smart_money + 20 * sector_resonance + 20 * core_score
        + 15 * rs_score + 10 * trend_integrity + 5 * freshness + 5 * MARKET_ENV_NEUTRAL
    ) / 100.0

    signals: List[str] = []
    if breakout_quality >= 65:
        signals.append("放量启动质量高")
    if rs_score >= 65:
        signals.append("跑赢大盘/板块")
    if sector_resonance >= 70:
        signals.append("板块共振强")
    if net_inflow_comp >= 65:
        signals.append("板块资金流入")
    if resilience >= 70:
        signals.append("缩量回调")
    if restart >= 60:
        signals.append("二次放量突破")
    if freshness >= 70:
        signals.append("信号新鲜")

    return {
        "code": entry["code"],
        "name": entry.get("name") or entry["code"],
        "price": closes[-1],
        "change_pct": round(entry.get("change_pct", 0.0), 2),
        "sector": (industry or {}).get("name"),
        "sector_code": (industry or {}).get("code"),
        "sector_type": "industry",
        "concept": (max(concepts, key=lambda c: c.get("score") or 0).get("name")
                    if concepts else None),
        "concept_code": (max(concepts, key=lambda c: c.get("score") or 0).get("code")
                         if concepts else None),
        "score": round(score, 1),
        "core_score": round(core_score, 1),
        "smart_money_score": round(smart_money, 1),
        "rs_score": round(rs_score, 1),
        "freshness": round(freshness, 1),
        "breakout_date": d_date or None,
        "breakout_days": max(0, days_since),
        "ret5_pct": round(ret5, 2),
        "components": {
            "breakout_quality": round(breakout_quality, 1),
            "volume_sustain": round(volume_sustain, 1),
            "relative_strength": round(rs_score, 1),
            "sector_relative": round(sector_rel_score, 1),
            "sector_resonance": round(sector_resonance, 1),
            "net_inflow": round(net_inflow_comp, 1),
            "amount": round(amount_comp, 1),
            "attention": round(attention, 1),
            "trend_integrity": round(trend_integrity, 1),
            "resilience": round(resilience, 1),
            "restart": round(restart, 1),
            "new_high": round(new_high, 1),
            "freshness": round(freshness, 1),
        },
        "signals": signals,
    }


def score_candidates(
    entries: List[dict],
    industry_of: Dict[str, dict],
    concepts_of: Dict[str, List[dict]],
    session_date: str,
    stock_meta: Optional[Dict[str, dict]] = None,
) -> List[dict]:
    """
    对候选池逐股打分，返回按综合评分排序的全部个股（不截断；截断与梯队归组由调用方处理）。

    entries: [{code,name,change_pct,breakout_date,breakout_volume,baseline_avg_volume,
               range_change_pct,hit_count}, ...]
    industry_of: code → 所属行业板块指标（含 name/change5_pct/net_inflow_pct/score）
    concepts_of: code → 所属概念板块指标列表（仅 Phase 1 热度 TOP 概念）
    stock_meta: code → 板块成分股指标（成交额 turnover / 换手 turnover_rate）
    """
    if not entries:
        return []

    stock_meta = stock_meta or {}
    idx_ret = {
        INDEX_HS300: _fetch_index_ret5(INDEX_HS300),
        INDEX_ZZ1000: _fetch_index_ret5(INDEX_ZZ1000),
    }

    scored: List[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {
            pool.submit(
                _score_one,
                e,
                _fetch_hist_tencent(e["code"], days=25),
                industry_of.get(e["code"]),
                concepts_of.get(e["code"]),
                idx_ret,
                stock_meta.get(e["code"]),
            ): e["code"]
            for e in entries
        }
        for fut in as_completed(futs):
            try:
                row = fut.result()
                if row:
                    scored.append(row)
            except Exception as e:
                logger.debug(f"个股评分异常 {futs[fut]}: {e}")

    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored

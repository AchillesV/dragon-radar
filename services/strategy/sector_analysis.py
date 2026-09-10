"""
「趋势 → 分析」板块聚合与热度计算（V2 Phase 1）

把当日「趋势候选池」放进「行业 / 概念板块」里做热度排名，输出每个重点板块的
热度、资金、量能、扩散度，并列出板块内的趋势候选股，帮前端「分析」Tab 找到
10~20 个资金正在形成共识的重点板块。

数据来源：腾讯证券板块接口（无需 Key，生产环境实测可用；刻意避开东财接口——东财
push2 系列在生产环境拿不到数据，见 trend.py 顶部说明）：
  * 板块列表 + 板块级指标：
      https://proxy.finance.qq.com/cgi/cgi-bin/rank/pt/getRank?board_type=hy|gn
    返回每个板块的：今日涨跌幅、5 日/20 日/60 日涨跌幅、主力净流入（今日/5日/20日）、
    上涨家数/成分股数、换手率、量比、成交额、领涨股等。
  * 板块成分股（行业全取，概念取热度 TOP，带分页）：
      https://proxy.finance.qq.com/cgi/cgi-bin/rank/hs/getBoardRankList?board_code=<板块>
    返回板块内每只个股的代码/名称/涨跌幅/换手/量比，用于计算扩散度（与候选池并集）
    并列出板块内的趋势候选股。

口径说明（已在 issue 中与仓库所有者确认）：
  1. 资金维度使用「板块级」主力净流入（腾讯板块接口直接提供），不做逐股净流入。
  2. 扩散度按「板块全成分股（腾讯板块成分股）」与「候选池内个股」的并集计算。
  3. 板块 5 日/20 日涨幅、资金、换手、量比全部来自腾讯板块接口的板块级指标。
"""
import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import requests

import stock_scores

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}
_BOARD_URL = "https://proxy.finance.qq.com/cgi/cgi-bin/rank/pt/getRank"
_MEMBER_URL = "https://proxy.finance.qq.com/cgi/cgi-bin/rank/hs/getBoardRankList"
_PAGE = 100

# 板块级指标缓存（板块数量级 ~830，一次分析约 10 个请求）
_BOARD_CACHE: Optional[Tuple[float, List[dict]]] = None
_BOARD_TTL = 300

# 板块成分股缓存（只对 TOP 板块拉取）
_MEMBER_CACHE: Dict[str, Tuple[float, List[dict]]] = {}
_MEMBER_TTL = 1800

# 返回给前端的板块数（行业/概念各取一部分，合计不超过该值）
TOP_INDUSTRY = 10
TOP_CONCEPT = 14

# 整体结果缓存（同一交易日 + 候选池规模，5 分钟内复用，避免重复拉 K 线/成分股）
_ANALYSIS_CACHE: Dict[str, Tuple[float, dict]] = {}
_ANALYSIS_TTL = 300


# ---------------------------------------------------------------------------
# 板块列表 + 板块级指标
# ---------------------------------------------------------------------------


def _to_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_board(item: dict) -> Optional[dict]:
    code = item.get("code")
    if not code:
        return None
    up = total = 0
    zgb = str(item.get("zgb") or "")
    if "/" in zgb:
        a, b = zgb.split("/", 1)
        up, total = int(_to_float(a)), int(_to_float(b))
    stock_type = str(item.get("stock_type") or "")
    return {
        "code": code,
        "name": item.get("name") or code,
        "type": "industry" if "HY" in stock_type else "concept",
        "change_pct": _to_float(item.get("zdf")),
        "change5_pct": _to_float(item.get("zdf_d5")),
        "change20_pct": _to_float(item.get("zdf_d20")),
        "turnover": _to_float(item.get("turnover")),          # 万元
        "net_inflow": _to_float(item.get("zljlr")),           # 主力净额（万元，今日）
        "net_inflow5": _to_float(item.get("zljlr_d5")),       # 主力净额（5日，万元）
        "turnover_rate": _to_float(item.get("hsl")),          # 换手率 %
        "lb": _to_float(item.get("lb")),                      # 量比
        "up_count": up,
        "total_count": total,
        "lead_stock": (item.get("lzg") or {}).get("name"),
        "lead_code": (item.get("lzg") or {}).get("code"),
    }


def _fetch_boards() -> List[dict]:
    """行业 + 概念板块清单与板块级指标（5 分钟内存缓存）。失败返回缓存的旧值或空列表。"""
    global _BOARD_CACHE
    now = time.time()
    if _BOARD_CACHE and now - _BOARD_CACHE[0] < _BOARD_TTL:
        return _BOARD_CACHE[1]

    boards: List[dict] = []
    for board_type in ("hy", "gn"):
        offset = 0
        while True:
            try:
                r = requests.get(_BOARD_URL, headers=_HEADERS, timeout=12, params={
                    "board_type": board_type,
                    "sort_type": "price",
                    "direct": "down",
                    "offset": str(offset),
                    "count": str(_PAGE),
                })
                data = (r.json() or {}).get("data") or {}
            except Exception as e:
                logger.warning(f"获取腾讯板块列表失败({board_type}, offset={offset}): {e}")
                break
            rows = data.get("rank_list") or []
            for it in rows:
                b = _parse_board(it)
                if b:
                    boards.append(b)
            total = int(_to_float(data.get("total"), 0))
            offset += len(rows)
            if not rows or offset >= total:
                break

    if boards:
        _BOARD_CACHE = (now, boards)
        logger.info(f"腾讯板块指标刷新: 共 {len(boards)} 个板块")
        return boards
    return _BOARD_CACHE[1] if _BOARD_CACHE else []


# ---------------------------------------------------------------------------
# 板块成分股（仅对 TOP 板块拉取，带分页）
# ---------------------------------------------------------------------------


def _fetch_members(code: str) -> List[dict]:
    now = time.time()
    cached = _MEMBER_CACHE.get(code)
    if cached and now - cached[0] < _MEMBER_TTL:
        return cached[1]

    members: List[dict] = []
    offset = 0
    while True:
        try:
            r = requests.get(_MEMBER_URL, headers=_HEADERS, timeout=12, params={
                "board_code": code,
                "sort_type": "price",
                "direct": "down",
                "offset": str(offset),
                "count": str(_PAGE),
            })
            data = (r.json() or {}).get("data") or {}
        except Exception as e:
            logger.debug(f"获取板块成分股失败 {code}: {e}")
            break
        rows = data.get("rank_list") or []
        for it in rows:
            c = str(it.get("code") or "")
            if not c:
                continue
            members.append({
                "code": c[2:] if c[:2].isalpha() else c,   # 去掉 sh/sz/bj 前缀
                "name": it.get("name") or c,
                "change_pct": _to_float(it.get("zdf")),
                "turnover": _to_float(it.get("turnover")),   # 成交额（万元）
                "turnover_rate": _to_float(it.get("hsl")),   # 换手率 %
                "lb": _to_float(it.get("lb")),               # 量比
            })
        total = int(_to_float(data.get("total"), 0))
        offset += len(rows)
        if not rows or offset >= total:
            break

    _MEMBER_CACHE[code] = (now, members)
    return members


def _fetch_members_batch(codes: List[str], max_workers: int = 5) -> Dict[str, List[dict]]:
    result: Dict[str, List[dict]] = {}
    if not codes:
        return result
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(_fetch_members, c): c for c in codes}
        for fut in as_completed(futs):
            code = futs[fut]
            try:
                result[code] = fut.result()
            except Exception as e:
                logger.debug(f"板块成分股获取异常 {code}: {e}")
                result[code] = []
    return result


# ---------------------------------------------------------------------------
# 归一化工具
# ---------------------------------------------------------------------------


def _norm(value: Optional[float], lo: float, hi: float) -> float:
    if value is None or hi <= lo:
        return 0.0
    return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100.0))


# ---------------------------------------------------------------------------
# 板块评分
# ---------------------------------------------------------------------------


def _score_board(board: dict, members: List[dict], candidates: List[dict]) -> dict:
    """
    计算单个板块的热度评分与扩散度。

    SectorScore（0~100）：
      10% 今日涨幅 + 15% 5日涨幅 + 8% 20日涨幅
      + 12% 今日资金(净额/成交额) + 10% 5日资金持续性(净额/成交额)
      + 12% 上涨家数占比 + 10% 强势股占比 + 8% 量比 + 15% 核心股强度
    """
    turnover = board["turnover"] or 0.0
    inflow_pct = (board["net_inflow"] / turnover * 100) if turnover else 0.0
    inflow5_pct = (board["net_inflow5"] / turnover * 100) if turnover else 0.0

    # ---- 扩散度：板块全成分股 ∪ 候选池个股 ----
    universe: Dict[str, float] = {}
    for m in members:
        universe[m["code"]] = m["change_pct"]
    for c in candidates:
        universe.setdefault(c["code"], c.get("change_pct", 0.0))

    changes = list(universe.values())
    total = len(changes)
    up_count = sum(1 for c in changes if c > 0)
    down_count = sum(1 for c in changes if c < 0)
    strong3 = sum(1 for c in changes if c >= 3.0)
    strong5 = sum(1 for c in changes if c >= 5.0)
    limit_up = sum(1 for c in changes if c >= 9.8)
    up_ratio = up_count / total * 100 if total else 0.0
    strong3_ratio = strong3 / total * 100 if total else 0.0
    limit_ratio = limit_up / total * 100 if total else 0.0
    breadth_score = up_ratio * 0.5 + strong3_ratio * 0.3 + min(100.0, limit_ratio * 5) * 0.2

    # 核心股强度：板块内候选股今日涨幅前 3 的均值
    top_changes = sorted([c.get("change_pct", 0.0) for c in candidates], reverse=True)[:3]
    core_strength = sum(top_changes) / len(top_changes) if top_changes else None

    score = (
        0.10 * _norm(board["change_pct"], -3.0, 6.0)
        + 0.15 * _norm(board["change5_pct"], -8.0, 15.0)
        + 0.08 * _norm(board["change20_pct"], -15.0, 30.0)
        + 0.12 * _norm(inflow_pct, -10.0, 10.0)
        + 0.10 * _norm(inflow5_pct, -15.0, 15.0)
        + 0.12 * up_ratio
        + 0.10 * strong3_ratio
        + 0.08 * _norm(board["lb"], 0.7, 2.5)
        + 0.15 * _norm(core_strength, -3.0, 10.0)
    )

    signals: List[str] = []
    if board["change5_pct"] > 3:
        signals.append("板块5日走强")
    if inflow_pct > 2:
        signals.append("主力净流入")
    if up_ratio >= 60:
        signals.append("上涨家数占优")
    if breadth_score >= 60:
        signals.append("扩散度良好")
    if limit_up:
        signals.append(f"{limit_up}只涨停")

    cand_members = []
    for c in sorted(candidates, key=lambda x: x.get("change_pct", 0.0), reverse=True):
        cand_members.append({
            "code": c["code"],
            "name": c.get("name") or c["code"],
            "change_pct": round(c.get("change_pct", 0.0), 2),
            "is_candidate": True,
            "is_lead": False,
        })
    if cand_members:
        cand_members[0]["is_lead"] = True

    return {
        "code": board["code"],
        "name": board["name"],
        "type": board["type"],
        "score": round(score, 1),
        "change_pct": round(board["change_pct"], 2),
        "change5_pct": round(board["change5_pct"], 2),
        "change20_pct": round(board["change20_pct"], 2),
        "lb": round(board["lb"], 2),
        "net_inflow_pct": round(inflow_pct, 2),
        "net_inflow5_pct": round(inflow5_pct, 2),
        "breadth_score": round(breadth_score, 1),
        "up_ratio": round(up_ratio, 1),
        "total_count": total,
        "up_count": up_count,
        "down_count": down_count,
        "strong3_count": strong3,
        "strong5_count": strong5,
        "limit_up_count": limit_up,
        "lead_stock": (cand_members[0]["name"] if cand_members else board.get("lead_stock")),
        "candidate_count": len(candidates),
        "candidates": cand_members,
        "signals": signals,
    }


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

# 内置 mock（真实数据源整体不可用时兜底，保证前端始终有结构可渲染）
_MOCK_ANALYSIS = {
    "source": "mock",
    "shortlist_count": 2,
    "core_count": 2,
    "stocks": [
        {
            "code": "000001", "name": "示例龙头", "price": 18.6, "change_pct": 9.9,
            "sector": "机器人", "sector_type": "industry", "concept": "人形机器人",
            "score": 89.4, "core_score": 92.0, "smart_money_score": 91.0, "rs_score": 88.0, "freshness": 86.0,
            "breakout_date": "2026-09-08", "breakout_days": 2, "ret5_pct": 12.4,
            "sector_code": "mock_1", "rank_in_sector": 1, "sector_size": 3,
            "ladder_role": "龙头", "is_core": True,
            "components": {
                "breakout_quality": 82.0, "volume_sustain": 74.0, "relative_strength": 88.0,
                "sector_resonance": 92.0, "net_inflow": 71.0, "resilience": 80.0,
                "restart": 65.0, "new_high": 90.0, "freshness": 86.0,
            },
            "signals": ["放量启动质量高", "跑赢大盘/板块", "板块共振强", "信号新鲜"],
        },
        {
            "code": "000002", "name": "示例中军", "price": 31.2, "change_pct": 6.2,
            "sector": "半导体", "sector_type": "industry", "concept": "国产芯片",
            "score": 81.2, "core_score": 79.0, "smart_money_score": 83.0, "rs_score": 79.0, "freshness": 74.0,
            "breakout_date": "2026-09-05", "breakout_days": 3, "ret5_pct": 8.1,
            "sector_code": "mock_2", "rank_in_sector": 2, "sector_size": 3,
            "ladder_role": "核心中军", "is_core": True,
            "components": {
                "breakout_quality": 70.0, "volume_sustain": 66.0, "relative_strength": 79.0,
                "sector_resonance": 86.0, "net_inflow": 62.0, "resilience": 72.0,
                "restart": 55.0, "new_high": 78.0, "freshness": 74.0,
            },
            "signals": ["跑赢大盘/板块", "板块共振强", "缩量回调"],
        },
    ],
    "sectors": [
        {
            "code": "mock_1", "name": "机器人", "type": "concept", "score": 92.0,
            "change_pct": 3.8, "change5_pct": 8.7, "change20_pct": 12.3, "lb": 1.6,
            "net_inflow_pct": 4.2, "net_inflow5_pct": 6.1, "breadth_score": 83.0, "up_ratio": 76.0,
            "total_count": 100, "up_count": 76, "down_count": 24, "strong3_count": 31,
            "strong5_count": 18, "limit_up_count": 6,
            "lead_stock": "示例龙头", "candidate_count": 4,
            "ladder": {
                "leader": [{"code": "000001", "name": "示例龙头", "score": 89.4, "core_score": 92.0, "change_pct": 9.9, "role": "龙头"}],
                "core": [{"code": "000002", "name": "示例中军", "score": 81.2, "core_score": 79.0, "change_pct": 6.2, "role": "核心中军"}],
                "trend": [{"code": "000003", "name": "示例跟随", "score": 72.0, "core_score": 70.0, "change_pct": 4.1, "role": "趋势跟随"}],
                "laggard": [],
            },
            "ladder_score": 80.0,
            "candidates": [
                {"code": "000001", "name": "示例龙头", "change_pct": 9.9, "is_candidate": True, "is_lead": True},
                {"code": "000002", "name": "示例中军", "change_pct": 6.2, "is_candidate": True, "is_lead": False},
            ],
            "signals": ["板块5日走强", "主力净流入", "上涨家数占优", "扩散度良好"],
        },
        {
            "code": "mock_2", "name": "半导体", "type": "industry", "score": 86.0,
            "change_pct": 2.1, "change5_pct": 6.4, "change20_pct": 9.1, "lb": 1.35,
            "net_inflow_pct": 3.1, "net_inflow5_pct": 4.4, "breadth_score": 74.0, "up_ratio": 68.0,
            "total_count": 100, "up_count": 68, "down_count": 32, "strong3_count": 22,
            "strong5_count": 12, "limit_up_count": 4,
            "lead_stock": "示例核心", "candidate_count": 3,
            "candidates": [
                {"code": "000003", "name": "示例核心", "change_pct": 7.8, "is_candidate": True, "is_lead": True},
            ],
            "signals": ["板块5日走强", "扩散度良好"],
        },
    ],
}


def _mock_result(session_date: str, candidate_count: int) -> dict:
    return dict(
        _MOCK_ANALYSIS,
        date=session_date,
        generated_at=datetime.datetime.now().isoformat(timespec="seconds"),
        candidate_count=candidate_count,
        shortlist_count=len(_MOCK_ANALYSIS.get("stocks", [])),
    )


def _heat_proxy(b: dict) -> float:
    """第一轮板块排序用的廉价热度（仅板块级指标）。"""
    return b["change5_pct"] * 0.5 + b["change_pct"] + b["lb"]


def _ladder_role(idx: int) -> str:
    """板块内按核心分排序后的梯队角色（设计文档 §13）。"""
    if idx == 0:
        return "龙头"
    if idx <= 2:
        return "核心中军"
    if idx <= 5:
        return "趋势跟随"
    return "补涨"


def _build_ladder(group: List[dict]) -> Tuple[dict, float]:
    """group 已按 core_score 降序。返回（四档梯队明细, 梯队完整度 0~100）。"""
    buckets: Dict[str, List[dict]] = {"leader": [], "core": [], "trend": [], "laggard": []}
    key_of = {"龙头": "leader", "核心中军": "core", "趋势跟随": "trend", "补涨": "laggard"}
    for i, st in enumerate(group):
        buckets[key_of[_ladder_role(i)]].append({
            "code": st["code"],
            "name": st["name"],
            "score": st["score"],
            "core_score": st["core_score"],
            "change_pct": st["change_pct"],
            "role": _ladder_role(i),
        })

    score = 0.0
    if buckets["leader"]:
        score += 30
    if buckets["core"]:
        score += 20
    if len(buckets["trend"]) >= 2:
        score += 20
    elif buckets["trend"]:
        score += 10
    if len(buckets["laggard"]) >= 2:
        score += 10
    if buckets["leader"] and buckets["leader"][0]["change_pct"] > 5:
        score += 10
    if sum(1 for s in group if s["change_pct"] > 0) >= 3:
        score += 10
    return buckets, min(100.0, score)


def build_analysis(candidates: List[dict], session_date: str) -> dict:
    """
    组装「趋势 → 分析」结果。

    candidates: [{code, name, change_pct, breakout_date, breakout_volume,
                  baseline_avg_volume, range_change_pct, hit_count}, ...]（当日趋势候选池）
    session_date: 最新交易日 YYYY-MM-DD

    流程：板块级指标排序 → 选定行业（全部，保证候选股都能归到行业）/ 概念（热度 TOP）→
    拉取成分股 → 用候选池计算核心股强度与扩散度 → 输出行业/概念重点板块 →
    逐股计算 SmartMoney / RS / Freshness / CoreScore（Phase 2~3），按综合分取 TOP SHORTLIST，
    其中前 CORE_COUNT 只为「核心股」，并给每个板块打上梯队（龙头/中军/趋势/补涨）。
    """
    boards = _fetch_boards()
    if not boards:
        logger.warning("腾讯板块指标为空，/analysis 退化到 mock")
        return _mock_result(session_date, len(candidates))

    cache_key = f"{session_date}|{len(candidates)}"
    cached = _ANALYSIS_CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < _ANALYSIS_TTL:
        return cached[1]

    cand_by_code = {c["code"]: c for c in candidates}

    industries = [b for b in boards if b["type"] == "industry"]
    top_concepts = sorted(
        [b for b in boards if b["type"] == "concept"],
        key=_heat_proxy, reverse=True,
    )[:TOP_CONCEPT]

    # 行业全部取成分股（候选股必然属于某个行业，保证候选池聚合完整）；
    # 概念只取热度 TOP（概念共 800+ 个，全量取成分股不现实）。
    picked = industries + top_concepts
    members_map = _fetch_members_batch([b["code"] for b in picked])

    def score_one(b: dict) -> dict:
        member_codes = {m["code"] for m in members_map.get(b["code"], [])}
        cands = [c for code, c in cand_by_code.items() if code in member_codes]
        return _score_board(b, members_map.get(b["code"], []), cands)

    industries_all = [score_one(b) for b in industries]
    concepts_all = [score_one(b) for b in top_concepts]
    industries_scored = sorted(industries_all, key=lambda s: s["score"], reverse=True)[:TOP_INDUSTRY]
    concepts_scored = sorted(concepts_all, key=lambda s: s["score"], reverse=True)

    sectors = sorted(industries_scored + concepts_scored,
                     key=lambda s: s["score"], reverse=True)

    # ---- 代码 → 板块 反查（供个股评分定位所属行业/概念） ----
    scored_by_code = {s["code"]: s for s in industries_all + concepts_all}
    industry_of: Dict[str, dict] = {}
    for b in industries:
        for m in members_map.get(b["code"], []):
            industry_of.setdefault(m["code"], scored_by_code[b["code"]])
    concepts_of: Dict[str, List[dict]] = {}
    for b in top_concepts:
        for m in members_map.get(b["code"], []):
            concepts_of.setdefault(m["code"], []).append(scored_by_code[b["code"]])

    # ---- 个股成交额/换手（来自板块成分股指标，供 CoreScore 用） ----
    stock_meta: Dict[str, dict] = {}
    for b in picked:
        for m in members_map.get(b["code"], []):
            stock_meta.setdefault(m["code"], m)

    # ---- Phase 2~3：逐股评分（SmartMoney / RS / Freshness / CoreScore） ----
    try:
        all_scored = stock_scores.score_candidates(
            candidates, industry_of, concepts_of, session_date, stock_meta
        )
    except Exception as e:
        logger.warning(f"个股评分失败，本轮跳过 stocks: {e}")
        all_scored = []

    # ---- 板块梯队：按所属行业板块的候选股 cohort 排序分档 + 梯队完整度 ----
    by_sector: Dict[str, List[dict]] = {}
    for st in all_scored:
        by_sector.setdefault(st.get("sector_code") or "", []).append(st)
    ladder_by_code: Dict[str, Tuple[dict, float]] = {}
    for scode, group in by_sector.items():
        if not scode:
            continue   # 未归入任何行业的个股不参与梯队
        group.sort(key=lambda s: s["core_score"], reverse=True)
        for i, st in enumerate(group):
            st["rank_in_sector"] = i + 1
            st["sector_size"] = len(group)
            st["ladder_role"] = _ladder_role(i)
        ladder_by_code[scode] = _build_ladder(group)
    for s in sectors:
        info = ladder_by_code.get(s["code"])
        if info:
            s["ladder"], s["ladder_score"] = info[0], round(info[1], 1)

    # ---- 重点池 TOP SHORTLIST，其中前 CORE_COUNT 只为核心股 ----
    stocks = all_scored[:stock_scores.SHORTLIST]
    for i, st in enumerate(stocks):
        st["is_core"] = i < stock_scores.CORE_COUNT
    core_count = min(stock_scores.CORE_COUNT, len(stocks))

    result = {
        "date": session_date,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "candidate_count": len(candidates),
        "shortlist_count": len(stocks),
        "core_count": core_count,
        "source": "tencent",
        "sectors": sectors,
        "stocks": stocks,
    }
    _ANALYSIS_CACHE[cache_key] = (now, result)
    return result

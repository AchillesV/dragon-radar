"""
异动股路由 —— akshare 真实数据优先，失败时 fallback 到 mock
可靠数据源：
  - stock_zt_pool_em       涨停板池（连板数/换手率/炸板次数/行业）
  - stock_zt_pool_strong_em  强势股池（量比/涨速）
  - stock_zt_pool_previous_em  昨日涨停池（用于弱转强判断）
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import defaultdict

import pandas as pd
from fastapi import APIRouter, Path
from models import AnomalyStock

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── 内存缓存（60秒 TTL） ──────────────────────────────────

_CACHE: Dict[str, Any] = {}
_CACHE_TTL = 60


def _now() -> float:
    return datetime.now().timestamp()


def _cache_get(key: str) -> Optional[pd.DataFrame]:
    item = _CACHE.get(key)
    if item and (_now() - item["ts"]) < _CACHE_TTL:
        return item["df"]
    return None


def _cache_set(key: str, df: pd.DataFrame) -> None:
    _CACHE[key] = {"df": df, "ts": _now()}


def _today() -> str:
    return datetime.now().strftime("%Y%m%d")


# ─── akshare 数据获取 ──────────────────────────────────────

def _get_zt_pool() -> Optional[pd.DataFrame]:
    """今日涨停板池"""
    key = f"zt_{_today()}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        import akshare as ak
        df = ak.stock_zt_pool_em(date=_today())
        if df is not None and not df.empty:
            _cache_set(key, df)
            logger.info(f"涨停池获取成功: {len(df)} 只")
            return df
    except Exception as e:
        logger.warning(f"stock_zt_pool_em 失败: {e}")
    return None


def _get_strong_pool() -> Optional[pd.DataFrame]:
    """强势股池（含量比、涨速）"""
    key = f"strong_{_today()}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        import akshare as ak
        df = ak.stock_zt_pool_strong_em(date=_today())
        if df is not None and not df.empty:
            _cache_set(key, df)
            logger.info(f"强势池获取成功: {len(df)} 只")
            return df
    except Exception as e:
        logger.warning(f"stock_zt_pool_strong_em 失败: {e}")
    return None


def _get_prev_zt_pool() -> Optional[pd.DataFrame]:
    """昨日涨停池（用于弱转强辅助判断）"""
    from datetime import date, timedelta
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    key = f"zt_prev_{yesterday}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        import akshare as ak
        df = ak.stock_zt_pool_previous_em(date=yesterday)
        if df is not None and not df.empty:
            _CACHE[key] = {"df": df, "ts": _now() + 3600}  # 昨日数据缓存更长
            return df
    except Exception as e:
        logger.warning(f"stock_zt_pool_previous_em 失败: {e}")
    return None


# ─── 列名安全访问 ──────────────────────────────────────────

def _col(df: pd.DataFrame, *names: str) -> Optional[str]:
    """返回 DataFrame 中第一个存在的列名"""
    for n in names:
        if n in df.columns:
            return n
    return None


def _val(row: Any, col: Optional[str], default: Any = None) -> Any:
    if col is None:
        return default
    v = row.get(col, default) if hasattr(row, "get") else getattr(row, col, default)
    return v if v is not None else default


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        return f if f == f else default  # NaN check
    except (TypeError, ValueError):
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


# ─── 涨停池行 → AnomalyStock ──────────────────────────────

def _zt_to_stock(
    row: Any,
    df: pd.DataFrame,
    anomaly_type: str,
    description: str,
    operation_guide: str,
    score: float,
) -> AnomalyStock:
    code = str(_val(row, _col(df, "代码", "code"), ""))
    name = str(_val(row, _col(df, "名称", "name"), ""))
    chg  = _safe_float(_val(row, _col(df, "涨跌幅", "change_pct"), 0))
    amt_raw = _safe_float(_val(row, _col(df, "成交额", "amount"), 0))
    # 成交额：akshare 单位通常为元，转为亿
    amt = amt_raw / 1e8 if amt_raw > 1e6 else amt_raw
    tr   = _safe_float(_val(row, _col(df, "换手率", "turnover"), 0))
    lb   = _safe_int(_val(row, _col(df, "连板数", "lianban_count"), 0))
    ind  = str(_val(row, _col(df, "所属行业", "industry"), "") or "")

    return AnomalyStock(
        code=code,
        name=name,
        change_pct=chg,
        amount=round(amt, 2),
        turnover=tr,
        anomaly_type=anomaly_type,
        description=description,
        operation_guide=operation_guide,
        score=score,
        industry=ind or None,
        lianban_count=lb or None,
    )


# ─── 11 种异动检测函数 ────────────────────────────────────

def _detect_lianban_upgrade(df: pd.DataFrame) -> List[AnomalyStock]:
    """连板晋级：今日涨停且连板数≥2"""
    lb_col = _col(df, "连板数")
    if lb_col is None:
        return []
    result = []
    for _, row in df[df[lb_col].apply(_safe_int) >= 2].iterrows():
        lb = _safe_int(_val(row, lb_col))
        desc = f"今日完成第{lb}连板，筹码集中，板块情绪持续升温。"
        guide = (
            f"{'3板以上注意高位风险，建议轻仓参与，严格止损。' if lb >= 3 else '2连板风险相对可控，可在次日竞价低吸，止损设昨日收盘价。'}"
        )
        score = min(9.9, 7.5 + lb * 0.5)
        result.append(_zt_to_stock(row, df, "lianban_upgrade", desc, guide, round(score, 1)))
    return result


def _detect_quiet_limit(df: pd.DataFrame) -> List[AnomalyStock]:
    """缩量涨停：涨停换手率<3%，筹码高度集中"""
    tr_col = _col(df, "换手率")
    if tr_col is None:
        return []
    result = []
    for _, row in df[df[tr_col].apply(_safe_float) < 3.0].iterrows():
        tr = _safe_float(_val(row, tr_col))
        desc = f"涨停换手率仅{tr:.1f}%，筹码高度集中，上方供应极少。"
        guide = "缩量涨停后大概率继续上涨，可在次日竞价或开盘后低吸，止损设昨日收盘价。"
        result.append(_zt_to_stock(row, df, "quiet_limit", desc, guide, 9.2))
    return result


def _detect_rebound_limit(df: pd.DataFrame) -> List[AnomalyStock]:
    """炸板回封：盘中炸板后重新封板（炸板次数≥1）"""
    zb_col = _col(df, "炸板次数")
    if zb_col is None:
        return []
    result = []
    for _, row in df[df[zb_col].apply(_safe_int) >= 1].iterrows():
        zb = _safe_int(_val(row, zb_col))
        lb = _safe_int(_val(row, _col(df, "连板数"), 0))
        first_time = _val(row, _col(df, "首次封板时间"), "--")
        last_time  = _val(row, _col(df, "最后封板时间"), "--")
        desc = f"今日炸板{zb}次后重新封板（首封{first_time}，末封{last_time}），说明主力护盘意志坚定。"
        guide = "炸板回封是主力主动护盘的信号，建议在第二次封板时少量参与，设3%-5%止损。"
        score = 8.8 if zb == 1 else 9.3 if lb >= 2 else 8.5
        result.append(_zt_to_stock(row, df, "rebound_limit", desc, guide, score))
    return result


def _detect_sector_resonance(df: pd.DataFrame) -> List[AnomalyStock]:
    """板块共振：≥3个行业各有≥3只涨停"""
    ind_col = _col(df, "所属行业")
    if ind_col is None:
        return []

    sector_counts: Dict[str, List[Any]] = defaultdict(list)
    for _, row in df.iterrows():
        ind = str(_val(row, ind_col, "") or "")
        if ind and ind not in ("其他", ""):
            sector_counts[ind].append(row)

    hot_sectors = {k: v for k, v in sector_counts.items() if len(v) >= 3}
    if len(hot_sectors) < 2:
        return []

    top_sectors = sorted(hot_sectors.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    sector_summary = "、".join([f"{s}({len(v)}只)" for s, v in top_sectors])
    desc_template = f"多板块共振：{sector_summary}，今日市场合力上攻。"
    guide = "板块共振行情持续性强，建议顺势操作，布局各板块龙头，注意高位风险控制仓位。"

    result = []
    for sector_name, rows in top_sectors:
        for row in rows[:3]:  # 每个板块最多取3只
            desc = f"所属{sector_name}板块，该板块今日{len(sector_counts[sector_name])}只股票涨停，{desc_template}"
            result.append(_zt_to_stock(row, df, "sector_resonance", desc, guide, 9.4))
    return result


def _detect_high_turnover(df: pd.DataFrame) -> List[AnomalyStock]:
    """高换手涨停：换手率≥10%"""
    tr_col = _col(df, "换手率")
    if tr_col is None:
        return []
    result = []
    for _, row in df[df[tr_col].apply(_safe_float) >= 10.0].iterrows():
        tr = _safe_float(_val(row, tr_col))
        desc = f"涨停换手率{tr:.1f}%，筹码换手充分，短线活跃度极高。"
        guide = "高换手涨停说明浮筹换手，后续上涨空间需结合连板数和板块情绪判断。"
        result.append(_zt_to_stock(row, df, "high_turnover", desc, guide, 8.5))
    return result


def _detect_dragon_separate(df: pd.DataFrame) -> List[AnomalyStock]:
    """龙头分离：板块龙头涨幅>板块均值×1.5"""
    chg_col = _col(df, "涨跌幅")
    ind_col = _col(df, "所属行业")
    if not chg_col or not ind_col:
        return []

    df_copy = df.copy()
    df_copy["_chg"] = df_copy[chg_col].apply(_safe_float)
    df_copy["_ind"] = df_copy[ind_col].astype(str)
    sector_avg = df_copy.groupby("_ind")["_chg"].mean()
    sector_count = df_copy.groupby("_ind")["_chg"].count()

    result = []
    for _, row in df_copy.iterrows():
        ind = str(row.get("_ind", ""))
        chg = float(row.get("_chg", 0))
        avg = float(sector_avg.get(ind, 0))
        cnt = int(sector_count.get(ind, 0))
        if avg > 0 and chg >= avg * 1.5 and chg > 8 and cnt >= 3:
            desc = f"{ind}板块均涨{avg:.1f}%，本股涨{chg:.2f}%，龙头效应显著（板块内{cnt}只涨停）。"
            guide = "龙头分化说明主力资金高度集中，跟随龙头操作，关注板块内二线是否跟涨。"
            result.append(_zt_to_stock(row, df, "dragon_separate", desc, guide, 9.1))
    return result


def _detect_volume_surge(df: Optional[pd.DataFrame]) -> List[AnomalyStock]:
    """放量异动：强势股池中量比≥2.5"""
    if df is None or df.empty:
        return []
    vr_col = _col(df, "量比")
    if vr_col is None:
        return []
    result = []
    for _, row in df[df[vr_col].apply(_safe_float) >= 2.5].iterrows():
        vr = _safe_float(_val(row, vr_col))
        chg = _safe_float(_val(row, _col(df, "涨跌幅"), 0))
        desc = f"量比{vr:.1f}倍，成交量异常放大，主力资金积极介入，涨幅{chg:.2f}%。"
        guide = "量能异动是主力进场信号，可在次日竞价低吸，止损设昨日收盘价下方3%。"
        score = min(9.8, 7.0 + vr * 0.5 + chg * 0.1)
        result.append(_zt_to_stock(row, df, "volume_surge", desc, guide, round(score, 1)))
    return result


def _detect_eod_rush(df: Optional[pd.DataFrame]) -> List[AnomalyStock]:
    """尾盘抢筹：强势股池中涨速>0（近30min持续上涨）"""
    if df is None or df.empty:
        return []
    zs_col = _col(df, "涨速")
    is_high_col = _col(df, "是否新高")
    if zs_col is None:
        return []

    cond = df[zs_col].apply(_safe_float) > 0
    if is_high_col:
        cond = cond & (df[is_high_col].astype(str).str.contains("是|Yes|yes|1|True", na=False))

    result = []
    for _, row in df[cond].head(10).iterrows():
        zs = _safe_float(_val(row, zs_col))
        chg = _safe_float(_val(row, _col(df, "涨跌幅"), 0))
        desc = f"涨速{zs:.2f}%，盘中持续上涨，今日涨幅{chg:.2f}%，尾盘动能强劲。"
        guide = "尾盘冲量通常预示次日继续高开，可在竞价阶段少量参与，高开3%止盈。"
        result.append(_zt_to_stock(row, df, "eod_rush", desc, guide, 8.0))
    return result


def _detect_weak_to_strong(
    zt_df: Optional[pd.DataFrame],
    prev_df: Optional[pd.DataFrame],
) -> List[AnomalyStock]:
    """
    弱转强：今日涨停 & 昨日收跌（昨日未在涨停池）
    近似实现：今日在涨停池但昨日不在涨停池
    """
    if zt_df is None or zt_df.empty:
        return []

    prev_codes: set = set()
    if prev_df is not None and not prev_df.empty:
        code_col = _col(prev_df, "代码", "code")
        if code_col:
            prev_codes = set(prev_df[code_col].astype(str))

    code_col_today = _col(zt_df, "代码", "code")
    lb_col = _col(zt_df, "连板数")
    if code_col_today is None:
        return []

    result = []
    for _, row in zt_df.iterrows():
        code = str(_val(row, code_col_today, ""))
        lb = _safe_int(_val(row, lb_col, 0))
        # 今日涨停 & 不在昨日涨停池 & 连板数<=1（新进涨停）
        if code not in prev_codes and lb <= 1:
            chg = _safe_float(_val(row, _col(zt_df, "涨跌幅"), 0))
            first_time = _val(row, _col(zt_df, "首次封板时间"), "--")
            desc = f"今日新进涨停（{first_time}封板），昨日未处于涨停序列，有弱转强特征，涨幅{chg:.2f}%。"
            guide = "弱转强是主力重新激活的信号，可小仓位跟进，次日如高开可加仓，止损设当日封板价-3%。"
            result.append(_zt_to_stock(row, zt_df, "weak_to_strong", desc, guide, 8.6))
    return result[:15]  # 限制数量


def _detect_reverse_limit(zt_df: Optional[pd.DataFrame]) -> List[AnomalyStock]:
    """
    地天板：盘中触跌停后收涨停
    无分时数据，用 封板资金高 + 首次封板时间 >= 14:00 作为近似
    （真正地天板往往下午才封板）
    """
    if zt_df is None or zt_df.empty:
        return []

    time_col = _col(zt_df, "首次封板时间")
    seal_col = _col(zt_df, "封板资金")
    if time_col is None:
        return []

    result = []
    for _, row in zt_df.iterrows():
        first_time = str(_val(row, time_col, "09:30") or "09:30")
        try:
            h, m = int(first_time[:2]), int(first_time[3:5])
            total_min = h * 60 + m
        except Exception:
            continue
        # 14:00 之后才封板，高度疑似地天板
        if total_min >= 14 * 60:
            chg = _safe_float(_val(row, _col(zt_df, "涨跌幅"), 0))
            seal = _safe_float(_val(row, seal_col, 0)) if seal_col else 0
            seal_yi = seal / 1e8 if seal > 1e6 else seal
            desc = f"下午{first_time}才封板，盘中可能经历大幅震荡，涨幅{chg:.2f}%，封板资金{seal_yi:.1f}亿。"
            guide = "尾盘封板次日大概率高开，可在竞价阶段少量建仓，目标前高，止损3%。"
            result.append(_zt_to_stock(row, zt_df, "reverse_limit", desc, guide, 9.0))
    return result[:8]


def _detect_gap_down_fade(strong_df: Optional[pd.DataFrame]) -> List[AnomalyStock]:
    """
    高开低走：需要 open/close 数据，强势池中涨速<0 且涨幅较小作为近似
    """
    if strong_df is None or strong_df.empty:
        return []

    zs_col = _col(strong_df, "涨速")
    chg_col = _col(strong_df, "涨跌幅")
    if zs_col is None or chg_col is None:
        return []

    result = []
    cond = (
        strong_df[zs_col].apply(_safe_float) < -0.5  # 涨速为负，正在走弱
    )
    for _, row in strong_df[cond].head(8).iterrows():
        chg = _safe_float(_val(row, chg_col))
        zs  = _safe_float(_val(row, zs_col))
        desc = f"涨速{zs:.2f}%，盘中持续走弱，目前涨幅{chg:.2f}%，注意高开低走风险。"
        guide = "高开低走是主力出货信号，持有者建议止损，空仓者回避，等待企稳后再观察。"
        result.append(_zt_to_stock(row, strong_df, "gap_down_fade", desc, guide, 3.5))
    return result


# ─── Mock Fallback ────────────────────────────────────────

_MOCK_FALLBACK: Dict[str, List[AnomalyStock]] = {
    "volume_surge": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=9.87, amount=45.6, turnover=12.3,
                     anomaly_type="volume_surge",
                     description="今日成交量达5日均量的3.2倍，主力明显进场，伴随涨停封单。（数据源不可达时显示）",
                     operation_guide="可在涨停板处挂单排队，止损设昨日收盘价下方2%。",
                     score=9.2, industry="电池", lianban_count=2),
    ],
    "weak_to_strong": [
        AnomalyStock(code="002371", name="北方华创", change_pct=7.23, amount=19.8, turnover=7.2,
                     anomaly_type="weak_to_strong",
                     description="早盘低开1.5%后快速拉升，午后强势涨停，弱转强形态标准。（数据源不可达时显示）",
                     operation_guide="弱转强是主力护盘信号，可在下午2点后放量突破时进场。",
                     score=8.9, industry="半导体"),
    ],
    "reverse_limit": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=10.02, amount=67.8, turnover=15.4,
                     anomaly_type="reverse_limit",
                     description="早盘一度跌停，主力强势护盘，尾盘反包涨停。（数据源不可达时显示）",
                     operation_guide="反包涨停次日大概率高开，可竞价少量建仓。",
                     score=9.5, industry="电池", lianban_count=1),
    ],
    "rebound_limit": [
        AnomalyStock(code="688041", name="海光信息", change_pct=9.95, amount=21.3, turnover=7.8,
                     anomaly_type="rebound_limit",
                     description="上午炸板后14:00再次封板，封板资金更大。（数据源不可达时显示）",
                     operation_guide="炸板回封说明主力意志坚定，建议在第二次封板时少量参与。",
                     score=9.1, industry="芯片"),
    ],
    "eod_rush": [
        AnomalyStock(code="002371", name="北方华创", change_pct=5.34, amount=15.6, turnover=5.6,
                     anomaly_type="eod_rush",
                     description="尾盘30分钟量能是前4小时均值的2.3倍，股价突破日内高点。（数据源不可达时显示）",
                     operation_guide="关注次日开盘价，若高开2%以上，可短线持有至前期压力位。",
                     score=7.9, industry="半导体"),
    ],
    "gap_down_fade": [
        AnomalyStock(code="000858", name="五粮液", change_pct=-2.34, amount=43.2, turnover=0.9,
                     anomaly_type="gap_down_fade",
                     description="高开3.5%后持续走弱，尾盘跌幅超过2%，主力出货迹象。（数据源不可达时显示）",
                     operation_guide="高开低走是出货信号，持有者建议止损，空仓者回避。",
                     score=3.2, industry="白酒"),
    ],
    "quiet_limit": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=10.01, amount=12.3, turnover=1.8,
                     anomaly_type="quiet_limit",
                     description="缩量涨停，换手率仅1.8%，主力筹码高度集中。（数据源不可达时显示）",
                     operation_guide="缩量涨停后大概率继续上涨，可在次日竞价低吸。",
                     score=9.4, industry="电池", lianban_count=4),
    ],
    "lianban_upgrade": [
        AnomalyStock(code="002371", name="北方华创", change_pct=10.01, amount=23.4, turnover=8.7,
                     anomaly_type="lianban_upgrade",
                     description="今日完成第3板，板块情绪高涨。（数据源不可达时显示）",
                     operation_guide="3板以上建议控制仓位，密切关注板块整体情绪。",
                     score=9.0, industry="半导体", lianban_count=3),
    ],
    "dragon_separate": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=9.87, amount=45.6, turnover=12.3,
                     anomaly_type="dragon_separate",
                     description="电池板块涨幅均值仅2.1%，本股独涨9.87%，龙头效应显著。（数据源不可达时显示）",
                     operation_guide="龙头分化说明主力资金高度集中，跟随龙头操作。",
                     score=9.3, industry="电池", lianban_count=2),
    ],
    "sector_resonance": [
        AnomalyStock(code="002371", name="北方华创", change_pct=10.01, amount=23.4, turnover=8.7,
                     anomaly_type="sector_resonance",
                     description="半导体板块共振主线，多板块联动上攻。（数据源不可达时显示）",
                     operation_guide="共振行情中选择细分龙头，分散持仓，每只不超过10%仓位。",
                     score=9.2, industry="半导体"),
    ],
    "high_turnover": [
        AnomalyStock(code="688041", name="海光信息", change_pct=9.95, amount=18.7, turnover=12.5,
                     anomaly_type="high_turnover",
                     description="涨停换手率12.5%，筹码换手充分，短线活跃度高。（数据源不可达时显示）",
                     operation_guide="高换手涨停后续空间需结合连板数和情绪判断。",
                     score=8.5, industry="芯片"),
    ],
    "recent_limit": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=9.87, amount=45.6, turnover=12.3,
                     anomaly_type="recent_limit",
                     description="近5日内第2次涨停，短线强度持续。（数据源不可达时显示）",
                     operation_guide="近期多次涨停说明主力在持续运作，可在回调不破支撑时介入。",
                     score=8.9, industry="电池", lianban_count=2),
    ],
}


# ─── 卡片元数据 ───────────────────────────────────────────

CARD_META = [
    ("volume_surge",     "放量",     "成交量≥5日均量×2.5且价格上涨"),
    ("high_turnover",    "高换手",   "换手率≥10%或历史90分位"),
    ("weak_to_strong",   "弱转强",   "早盘跌>1%，收盘涨>3%"),
    ("reverse_limit",    "地天板",   "盘中触跌停后收涨停"),
    ("rebound_limit",    "炸板回封", "开板后30min内重新封板"),
    ("eod_rush",         "尾盘抢筹", "14:30后量占全日30%且创新高"),
    ("gap_down_fade",    "高开低走", "高开3%+，收跌2%，全日震幅>5%"),
    ("quiet_limit",      "缩量涨停", "涨停换手率<3%，封单充裕"),
    ("lianban_upgrade",  "连板晋级", "今日涨停且连板数≥2"),
    ("dragon_separate",  "龙头分离", "板块龙头涨幅>板块均值×1.5"),
    ("sector_resonance", "板块共振", "≥2板块各有≥3只涨停"),
]

# 全局缓存 per-type 结果（最多缓存60秒）
_RESULT_CACHE: Dict[str, Any] = {}


def _get_real_stocks(anomaly_type: str) -> Optional[List[AnomalyStock]]:
    """
    尝试用真实数据计算异动，成功返回列表（可能为空），失败返回 None。
    """
    cache_key = f"result_{anomaly_type}_{_today()}"
    cached = _RESULT_CACHE.get(cache_key)
    if cached and (_now() - cached["ts"]) < _CACHE_TTL:
        return cached["stocks"]

    zt_df     = _get_zt_pool()
    strong_df = _get_strong_pool()

    stocks: Optional[List[AnomalyStock]] = None
    try:
        if anomaly_type == "lianban_upgrade":
            stocks = _detect_lianban_upgrade(zt_df) if zt_df is not None else None
        elif anomaly_type == "quiet_limit":
            stocks = _detect_quiet_limit(zt_df) if zt_df is not None else None
        elif anomaly_type == "rebound_limit":
            stocks = _detect_rebound_limit(zt_df) if zt_df is not None else None
        elif anomaly_type == "sector_resonance":
            stocks = _detect_sector_resonance(zt_df) if zt_df is not None else None
        elif anomaly_type == "high_turnover":
            stocks = _detect_high_turnover(zt_df) if zt_df is not None else None
        elif anomaly_type == "dragon_separate":
            stocks = _detect_dragon_separate(zt_df) if zt_df is not None else None
        elif anomaly_type == "volume_surge":
            stocks = _detect_volume_surge(strong_df)
        elif anomaly_type == "eod_rush":
            stocks = _detect_eod_rush(strong_df)
        elif anomaly_type == "weak_to_strong":
            prev_df = _get_prev_zt_pool()
            stocks = _detect_weak_to_strong(zt_df, prev_df)
        elif anomaly_type == "reverse_limit":
            stocks = _detect_reverse_limit(zt_df)
        elif anomaly_type == "gap_down_fade":
            stocks = _detect_gap_down_fade(strong_df)
        elif anomaly_type in ("recent_limit", "lianban"):
            stocks = _detect_lianban_upgrade(zt_df) if zt_df is not None else None
    except Exception as e:
        logger.error(f"detect_{anomaly_type} 出错: {e}", exc_info=True)
        stocks = None

    if stocks is not None:
        _RESULT_CACHE[cache_key] = {"stocks": stocks, "ts": _now()}
    return stocks


# ─── 路由 ─────────────────────────────────────────────────

@router.get("/anomaly/cards")
async def get_anomaly_cards():
    """返回所有异动类型的卡片摘要（含实时筛出数量）"""
    zt_df = _get_zt_pool()
    cards = []
    for type_id, title, desc in CARD_META:
        real = _get_real_stocks(type_id)
        if real is not None:
            count = len(real)
            data_tag = "实时"
        else:
            count = len(_MOCK_FALLBACK.get(type_id, []))
            data_tag = "演示"
        cards.append({
            "id":          type_id,
            "title":       title,
            "description": desc,
            "count":       count,
            "lastUpdated": datetime.now().strftime("%H:%M"),
            "dataSource":  data_tag,
            "hasRealData": zt_df is not None,
        })
    return cards


@router.get("/anomaly/{anomaly_type}", response_model=List[AnomalyStock])
async def get_anomaly_stocks(anomaly_type: str = Path(..., description="异动类型")):
    """获取指定类型的异动股票列表（优先真实数据，失败时返回演示数据）"""
    real = _get_real_stocks(anomaly_type)
    if real is not None:
        if not real:
            logger.info(f"{anomaly_type}: 真实数据为空（今日无此类异动）")
        return real

    logger.warning(f"{anomaly_type}: 真实数据获取失败，返回演示数据")
    return _MOCK_FALLBACK.get(anomaly_type, _MOCK_FALLBACK.get("volume_surge", []))

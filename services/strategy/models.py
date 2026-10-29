from pydantic import BaseModel
from typing import Optional, List, Any, Dict


class AnomalyStock(BaseModel):
    code: str
    name: str
    change_pct: float
    amount: float
    turnover: float
    anomaly_type: str
    description: str
    operation_guide: str
    score: Optional[float] = None
    industry: Optional[str] = None
    lianban_count: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


class FeatureInfo(BaseModel):
    id: str
    name: str
    description: str
    is_default: bool = False


class CandidateStock(BaseModel):
    code: str
    name: str
    change_pct: float
    amount: float
    turnover: float
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    circ_market_cap: Optional[float] = None
    pe: Optional[float] = None
    price: Optional[float] = None
    lianban_count: Optional[int] = None
    matched_features: List[str] = []
    description: Optional[str] = None   # 触发前端 feature-tag 渲染
    score: Optional[float] = None


class FilterRequest(BaseModel):
    codes: List[str]
    filters: Optional[Dict[str, Any]] = None


class MainlineStock(BaseModel):
    """主线核心票 —— 2026-04-01~2026-06-30 累计涨幅 >=80% 的全市场股票（已剔除创业板/科创板/ST）"""
    code: str
    name: str
    price: Optional[float] = None
    change_pct: float = 0.0          # 今日涨跌幅
    amount: Optional[float] = None   # 今日成交额（元）
    period_gain_pct: float = 0.0     # 4/1~6/30 累计涨幅（已用真实历史行情验证）
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class CoreSector(BaseModel):
    """热门板块（核心模块）—— 涨停扩散 + 放量 + 资金净流入 + 高度"""
    name: str                              # 涨停池「所属行业」原始名
    matched_name: Optional[str] = None     # 对齐后的同花顺行业名（缺失代表板块数据不可得）
    limit_up_count: int = 0                # 今日涨停家数
    max_board: int = 0                     # 板块最高连板
    multi_board_count: int = 0             # 连板 >= 2 的家数
    one_board_count: int = 0               # 首板家数
    main_net_today: Optional[float] = None  # 今日资金净额（亿）
    main_net_5d: Optional[float] = None     # 5 日资金净额（亿）
    main_net_10d: Optional[float] = None    # 10 日资金净额（亿）
    amount_today: Optional[float] = None    # 今日板块成交额（亿）
    volume_ratio: Optional[float] = None    # 近3日均额 / 前20日均额
    rise_ratio: Optional[float] = None      # 上涨家数占比
    score: float = 0.0
    reasons: List[str] = []


class CoreStock(BaseModel):
    """核心候选 —— 热门板块内的首板票"""
    code: str
    name: str
    sector: str
    price: Optional[float] = None
    change_pct: float = 0.0
    amount: Optional[float] = None          # 今日成交额（元）
    seal_amount: Optional[float] = None     # 封板资金（元）
    turnover_rate: Optional[float] = None   # 换手率（%）
    first_limit_time: Optional[str] = None  # 首次封板时间 HH:MM:SS
    break_count: int = 0                    # 炸板次数
    limit_stat: Optional[str] = None        # 涨停统计，如 1/1
    sector_score: float = 0.0


class CoreResult(BaseModel):
    """核心页面整体结果"""
    date: str
    generated_at: str
    market_max_board: int = 0
    data_quality: str = "full"              # full | partial（板块资金/放量数据缺失）
    sectors: List[CoreSector] = []
    watchlist: List[CoreSector] = []        # 扩散+高度达标，但资金/放量未达标的板块
    stocks: List[CoreStock] = []


class TrendStock(BaseModel):
    """「趋势」命中股票 —— 放量启动 + 持续放量 + 横盘"""
    code: str
    name: str
    price: Optional[float] = None
    change: Optional[float] = None        # 今日涨跌额
    change_pct: float                     # 今日涨跌幅（百分比）
    industry: Optional[str] = None
    breakout_date: str              # 放量日 D
    breakout_volume: float
    baseline_avg_volume: float      # 放量前 5 日基准均量
    range_window: str               # 命中横盘条件的窗口："3日" / "5日" / "10日"
    range_change_pct: float         # 该窗口累计涨跌幅
    description: Optional[str] = None
    hit_count: int = 1               # 过去统计周期内的入选次数（不要求连续），>=3 视为持续入选


class SectorMember(BaseModel):
    """板块内个股（候选池个股 or 板块成分股）"""
    code: str
    name: str
    change_pct: float = 0.0
    is_candidate: bool = False       # 是否来自趋势候选池
    is_lead: bool = False            # 是否为本板块候选池领涨股


class LadderStock(BaseModel):
    """板块梯队里的单只个股"""
    code: str
    name: str
    score: float = 0.0           # 综合评分
    core_score: float = 0.0      # 核心股评分
    change_pct: float = 0.0
    role: str = ""               # 龙头 / 核心中军 / 趋势跟随 / 补涨


class SectorLadder(BaseModel):
    """板块梯队（龙头 / 中军 / 趋势 / 补涨）"""
    leader: List[LadderStock] = []
    core: List[LadderStock] = []
    trend: List[LadderStock] = []
    laggard: List[LadderStock] = []


class SectorAnalysis(BaseModel):
    """「趋势 → 分析」单个板块的热度、资金与扩散度"""
    code: str                        # 腾讯板块代码
    name: str
    type: str                        # industry | concept
    score: float                     # 板块热度 0~100
    change_pct: float = 0.0          # 今日板块涨跌幅
    change5_pct: Optional[float] = None     # 5 日涨跌幅
    change20_pct: Optional[float] = None    # 20 日涨跌幅
    lb: Optional[float] = None              # 量比
    net_inflow_pct: Optional[float] = None  # 今日主力净额 / 成交额（%）
    net_inflow5_pct: Optional[float] = None # 5 日主力净额 / 成交额（%）
    breadth_score: Optional[float] = None   # 扩散度 0~100
    up_ratio: Optional[float] = None        # 上涨家数占比 %
    total_count: int = 0                    # 参与扩散度计算的股票数（并集）
    up_count: int = 0
    down_count: int = 0
    strong3_count: int = 0           # 涨幅 >= 3% 的成分股数
    strong5_count: int = 0           # 涨幅 >= 5% 的成分股数
    limit_up_count: int = 0          # 涨停成分股数（>=9.8%）
    lead_stock: Optional[str] = None
    candidate_count: int = 0         # 板块内趋势候选股数量
    candidates: List[SectorMember] = []
    ladder: Optional[SectorLadder] = None   # 板块梯队（龙头/中军/趋势/补涨）
    ladder_score: Optional[float] = None    # 梯队完整度 0~100
    signals: List[str] = []          # 策略信号（非买卖结论）


class TrendScoreComponents(BaseModel):
    """个股评分各分项（0~100，供前端展开）"""
    breakout_quality: Optional[float] = None   # 放量启动质量
    volume_sustain: Optional[float] = None     # 启动后量能保持
    relative_strength: Optional[float] = None  # 个股相对强度
    sector_relative: Optional[float] = None    # 板块内相对强度
    sector_resonance: Optional[float] = None   # 板块共振
    net_inflow: Optional[float] = None         # 资金（板块级代理）
    amount: Optional[float] = None              # 成交额
    attention: Optional[float] = None           # 市场关注度（换手率）
    trend_integrity: Optional[float] = None     # 趋势完整性
    resilience: Optional[float] = None         # 回调资金稳定性（缩量回调）
    restart: Optional[float] = None            # 再次放量突破
    new_high: Optional[float] = None           # 新高/突破
    freshness: Optional[float] = None          # 资金信号新鲜度


class TrendStockScore(BaseModel):
    """「趋势 → 分析」重点股（Phase 2~3：Smart Money / RS / Freshness / 核心股）"""
    code: str
    name: str
    price: Optional[float] = None
    change_pct: float = 0.0
    sector: Optional[str] = None               # 所属行业板块
    sector_code: Optional[str] = None          # 所属行业板块代码
    sector_type: Optional[str] = None
    concept: Optional[str] = None              # 命中的最强概念板块
    concept_code: Optional[str] = None
    score: float = 0.0                         # 综合评分 FinalScore（0~100）
    core_score: float = 0.0                    # 核心股评分 CoreScore
    smart_money_score: float = 0.0             # 资金行为评分
    rs_score: float = 0.0                      # 相对强度评分
    freshness: float = 0.0                     # 资金信号新鲜度
    rank_in_sector: Optional[int] = None       # 所属板块内排名
    sector_size: Optional[int] = None          # 所属板块候选股数量
    ladder_role: Optional[str] = None          # 梯队角色：龙头/核心中军/趋势跟随/补涨
    is_core: bool = False                      # 是否进入核心股 TOP
    breakout_date: Optional[str] = None        # 放量启动日
    breakout_days: int = 0                     # 距启动的交易日数
    lifecycle_stage: int = 1                   # 资金生命周期阶段 1~6
    lifecycle_label: str = ""                  # 阶段名：试探/启动/确认/加速/分歧/撤退
    lifecycle_path: List[str] = []             # 阶段路径（用于回放展示）
    buy_status: str = ""                       # 买点状态枚举
    buy_status_label: str = ""                 # 买点状态中文名
    is_pick: bool = False                      # 是否进入最终交易标的（5~10 只）
    ret5_pct: Optional[float] = None           # 近 5 日涨幅 %
    components: TrendScoreComponents = TrendScoreComponents()
    signals: List[str] = []


class TrendAnalysis(BaseModel):
    """「趋势 → 分析」页面数据"""
    date: str
    generated_at: str
    candidate_count: int             # 参与聚合的趋势候选股数量
    shortlist_count: int = 0         # Phase 2 压缩后的重点股数量
    core_count: int = 0              # Phase 3 核心股数量
    final_count: int = 0             # Phase 4 最终交易标的数量（5~10）
    source: str = "tencent"         # 数据来源：tencent | mock
    sectors: List[SectorAnalysis] = []
    stocks: List[TrendStockScore] = []


# ---------------------------------------------------------------------------
# Phase 5：策略回测（T+1/T+3/T+5/T+10）
# ---------------------------------------------------------------------------
class BacktestStats(BaseModel):
    """单个持有周期的回测统计"""
    horizon: int
    samples: int = 0
    win_rate: Optional[float] = None       # 胜率 %
    avg_ret: Optional[float] = None        # 平均收益 %
    median_ret: Optional[float] = None     # 收益中位数 %
    avg_win: Optional[float] = None        # 平均盈利 %
    avg_loss: Optional[float] = None       # 平均亏损 %
    payoff_ratio: Optional[float] = None   # 盈亏比
    profit_factor: Optional[float] = None  # 盈亏总额比
    expectancy: Optional[float] = None     # 期望收益 %
    max_drawdown: Optional[float] = None   # 区间平均最大浮亏 %
    best: Optional[float] = None
    worst: Optional[float] = None


class BacktestGroup(BaseModel):
    """按买点状态 / 生命周期分组的 T+5 统计"""
    key: str
    label: str = ""
    samples: int = 0
    win_rate: Optional[float] = None
    avg_ret5: Optional[float] = None


class BacktestDateRow(BaseModel):
    """单个信号日的回测行"""
    date: str
    candidates: int = 0
    signals: int = 0
    avg_ret5: Optional[float] = None
    win_rate5: Optional[float] = None


class TrendBacktest(BaseModel):
    """「趋势 → 分析」策略回测结果"""
    generated_at: str
    date_from: str = ""
    date_to: str = ""
    sessions: int = 0
    universe_size: int = 0
    signal_total: int = 0
    horizons: List[int] = []
    stats: List[BacktestStats] = []
    by_buy_status: List[BacktestGroup] = []
    by_lifecycle: List[BacktestGroup] = []
    dates: List[BacktestDateRow] = []
    source: str = "tencent"
    note: str = ""

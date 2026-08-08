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


class MainlineSectorFlow(BaseModel):
    """科技主线子板块 —— 当日主力资金净流入额加总（元）"""
    id: str
    name: str
    group: str                       # 半导体 / 算力硬件
    hot: bool = False                # 是否为用户标注的热门子板块
    net_inflow: float = 0.0          # 子板块内所有分类票当日主力净流入额加总（元）
    stock_count: int = 0             # 参与加总的分类票数量
    matched_count: int = 0           # 实际取到资金流数据的股票数（<stock_count 说明部分取数失败）


class MainlineStock(BaseModel):
    """科技主线核心票 —— 2026-04-01~2026-06-30 累计涨幅翻倍的科技股"""
    code: str
    name: str
    subsectors: List[str]            # 所属子板块 id 列表（可能跨多个子板块）
    price: Optional[float] = None
    change_pct: float = 0.0          # 今日涨跌幅
    amount: Optional[float] = None   # 今日成交额（元）
    period_gain_pct: float = 0.0     # 4/1~6/30 累计涨幅（已用真实历史行情验证）
    period_start: Optional[str] = None
    period_end: Optional[str] = None


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

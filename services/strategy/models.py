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


class TrendStock(BaseModel):
    """「趋势」命中股票 —— 放量启动 + 持续放量 + 横盘"""
    code: str
    name: str
    price: Optional[float] = None
    change_pct: float
    industry: Optional[str] = None
    breakout_date: str              # 放量日 D
    breakout_volume: float
    baseline_avg_volume: float      # 放量前 5 日基准均量
    range_window: str               # 命中横盘条件的窗口："3日" / "5日" / "10日"
    range_change_pct: float         # 该窗口累计涨跌幅
    description: Optional[str] = None

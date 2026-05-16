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

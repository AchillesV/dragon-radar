from pydantic import BaseModel
from typing import Optional, List, Any, Dict


class StockData(BaseModel):
    code: str
    name: str
    change_pct: float
    amount: float
    turnover: float
    lianban_count: Optional[int] = 0
    sectors: Optional[List[str]] = []
    recent_trend: Optional[str] = "震荡上行"
    pe: Optional[float] = None
    pb: Optional[float] = None
    market_cap: Optional[float] = None


class StockReport(BaseModel):
    code: str
    name: str
    date: str
    content: str
    model: Optional[str] = "mock"
    from_cache: bool = False


class MarketOverviewInput(BaseModel):
    date: Optional[str] = None
    rise_count: Optional[int] = 2341
    fall_count: Optional[int] = 985
    limit_up_count: Optional[int] = 87
    total_amount: Optional[float] = 2.87
    max_lianban: Optional[int] = 11
    max_lianban_stock: Optional[str] = "某科技"
    sectors: Optional[List[str]] = []


class BulkAnalysisRequest(BaseModel):
    stock_codes: List[str]
    market_data: Optional[MarketOverviewInput] = None


class BulkAnalysisResult(BaseModel):
    date: str
    content: str
    stock_count: int
    model: Optional[str] = "mock"

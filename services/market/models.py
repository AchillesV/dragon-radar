from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class StockSnapshot(BaseModel):
    code: str
    name: str
    price: float
    change_pct: float
    volume: int
    amount: float
    turnover: float
    pe: Optional[float] = None
    pb: Optional[float] = None
    market_cap: Optional[float] = None
    lianban_count: Optional[int] = None
    industry: Optional[str] = None
    is_st: bool = False


class MarketOverview(BaseModel):
    date: str
    rise_count: int
    fall_count: int
    flat_count: int
    limit_up_count: int
    limit_down_count: int
    total_amount: float          # 单位：万亿
    average_turnover: float
    sentiment_index: float       # 0-100


class SectorRank(BaseModel):
    name: str
    change_pct: float
    leading_stock: str
    leading_change: float
    total_amount: Optional[float] = None
    rise_count: Optional[int] = None
    fall_count: Optional[int] = None


class FundFlowItem(BaseModel):
    name: str
    net_inflow: float            # 单位：亿元
    main_inflow: float
    retail_inflow: float
    leading_stock: Optional[str] = None


class LianbanStock(BaseModel):
    code: str
    name: str
    count: int                   # 连板数
    reason: Optional[str] = None
    first_limit_time: Optional[str] = None
    amount: Optional[float] = None


class LianbanTier(BaseModel):
    count: int                   # 第几板
    stocks: List[LianbanStock]


class DailyAmount(BaseModel):
    date: str
    amount: float                # 单位：万亿
    change_pct: Optional[float] = None

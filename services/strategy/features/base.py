from abc import ABC, abstractmethod
from typing import List
from datetime import date


class BaseFeature(ABC):
    id: str
    name: str

    @abstractmethod
    def screen(self, stocks: List[dict], target_date: date) -> List[dict]:
        """筛选满足特征的股票，返回股票列表（可附加 meta 信息）"""
        pass

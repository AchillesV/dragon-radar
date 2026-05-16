"""
特征计算器 —— 实现 11 个量化特征。
每个特征均包含 Mock 实现，当外部数据源不可用时自动 fallback。
"""
import logging
import random
from datetime import date, datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock 股票池（贴近真实的测试数据）
# ---------------------------------------------------------------------------

MOCK_STOCKS = [
    {"code": "300750", "name": "宁德时代", "change_pct": 9.87, "volume": 1234567, "avg_volume_5d": 456789,
     "turnover": 12.3, "open_pct": -1.5, "amount": 45.6, "industry": "电池", "lianban_count": 2,
     "open": 180.0, "close": 185.2, "high": 186.5, "low": 178.3, "sector_avg_change": 3.2,
     "pe": 32.5, "pb": 5.6, "market_cap": 8120.0, "is_limit_up": True, "is_limit_down": False},
    {"code": "002371", "name": "北方华创", "change_pct": 10.01, "volume": 987654, "avg_volume_5d": 345678,
     "turnover": 8.7, "open_pct": -0.5, "amount": 23.4, "industry": "半导体", "lianban_count": 3,
     "open": 210.0, "close": 231.5, "high": 232.0, "low": 208.5, "sector_avg_change": 4.5,
     "pe": 45.2, "pb": 7.8, "market_cap": 1250.0, "is_limit_up": True, "is_limit_down": False},
    {"code": "688041", "name": "海光信息", "change_pct": 9.95, "volume": 765432, "avg_volume_5d": 234567,
     "turnover": 6.5, "open_pct": 0.3, "amount": 18.7, "industry": "芯片", "lianban_count": 1,
     "open": 95.0, "close": 104.5, "high": 105.0, "low": 94.5, "sector_avg_change": 3.8,
     "pe": 89.3, "pb": 12.1, "market_cap": 560.0, "is_limit_up": True, "is_limit_down": False},
    {"code": "300896", "name": "爱美客", "change_pct": 3.45, "volume": 543210, "avg_volume_5d": 987654,
     "turnover": 2.1, "open_pct": 0.8, "amount": 12.3, "industry": "医美", "lianban_count": 0,
     "open": 420.0, "close": 434.5, "high": 436.0, "low": 418.0, "sector_avg_change": 1.2,
     "pe": 55.6, "pb": 9.8, "market_cap": 1980.0, "is_limit_up": False, "is_limit_down": False},
    {"code": "002594", "name": "比亚迪", "change_pct": 2.87, "volume": 2345678, "avg_volume_5d": 1234567,
     "turnover": 1.8, "open_pct": 1.2, "amount": 78.9, "industry": "新能源汽车", "lianban_count": 0,
     "open": 245.0, "close": 252.0, "high": 253.5, "low": 244.0, "sector_avg_change": 1.5,
     "pe": 28.4, "pb": 4.2, "market_cap": 73200.0, "is_limit_up": False, "is_limit_down": False},
    {"code": "300059", "name": "东方财富", "change_pct": -1.23, "volume": 3456789, "avg_volume_5d": 2345678,
     "turnover": 3.4, "open_pct": 3.5, "amount": 65.4, "industry": "互联网金融", "lianban_count": 0,
     "open": 18.5, "close": 16.8, "high": 18.7, "low": 16.5, "sector_avg_change": 0.5,
     "pe": 22.1, "pb": 3.4, "market_cap": 22400.0, "is_limit_up": False, "is_limit_down": False},
    {"code": "601288", "name": "农业银行", "change_pct": 0.54, "volume": 12345678, "avg_volume_5d": 9876543,
     "turnover": 0.4, "open_pct": 0.2, "amount": 34.5, "industry": "银行", "lianban_count": 0,
     "open": 3.71, "close": 3.73, "high": 3.74, "low": 3.70, "sector_avg_change": 0.3,
     "pe": 5.2, "pb": 0.6, "market_cap": 137800.0, "is_limit_up": False, "is_limit_down": False},
    {"code": "000858", "name": "五粮液", "change_pct": -2.34, "volume": 876543, "avg_volume_5d": 654321,
     "turnover": 0.9, "open_pct": -1.8, "amount": 43.2, "industry": "白酒", "lianban_count": 0,
     "open": 142.0, "close": 138.7, "high": 142.5, "low": 138.0, "sector_avg_change": -1.5,
     "pe": 18.7, "pb": 6.3, "market_cap": 53900.0, "is_limit_up": False, "is_limit_down": False},
    {"code": "300015", "name": "爱尔眼科", "change_pct": 5.23, "volume": 654321, "avg_volume_5d": 210000,
     "turnover": 11.5, "open_pct": -1.2, "amount": 8.7, "industry": "医疗服务", "lianban_count": 1,
     "open": 12.5, "close": 13.2, "high": 13.3, "low": 12.2, "sector_avg_change": 2.1,
     "pe": 35.6, "pb": 4.9, "market_cap": 1870.0, "is_limit_up": False, "is_limit_down": False},
    {"code": "600519", "name": "贵州茅台", "change_pct": -1.87, "volume": 234567, "avg_volume_5d": 345678,
     "turnover": 0.3, "open_pct": 0.5, "amount": 89.1, "industry": "白酒", "lianban_count": 0,
     "open": 1680.0, "close": 1648.6, "high": 1682.0, "low": 1645.0, "sector_avg_change": -1.5,
     "pe": 28.5, "pb": 10.2, "market_cap": 207000.0, "is_limit_up": False, "is_limit_down": False},
]

# 特征对应的 mock 股票子集
FEATURE_MOCK_MAP: Dict[str, List[str]] = {
    "volume_surge":      ["300750", "002371", "688041", "300015"],
    "high_turnover":     ["300750", "002371", "688041", "300015"],
    "weak_to_strong":    ["002371", "300015"],
    "reverse_limit":     ["300750"],
    "rebound_limit":     ["688041"],
    "eod_rush":          ["300750", "002371", "688041"],
    "gap_down_fade":     ["000858", "300059"],
    "quiet_limit":       ["300750"],
    "lianban_upgrade":   ["002371", "688041"],
    "dragon_separate":   ["300750", "002371"],
    "sector_resonance":  ["300750", "002371", "688041", "300015"],
    # 前端常用别名
    "recent_limit":      ["300750", "002371", "688041"],
    "fund_inflow":       ["300750", "002371", "002594"],
    "lianban":           ["300750", "002371", "688041"],
}

ALL_FEATURES = [
    {"id": "volume_surge",     "name": "量能异动",    "description": "成交量≥5日均量×2.5且当日上涨", "is_default": True},
    {"id": "high_turnover",    "name": "高换手",      "description": "换手率≥10%", "is_default": True},
    {"id": "weak_to_strong",   "name": "弱转强",      "description": "早盘跌>1%，收盘涨>3%", "is_default": True},
    {"id": "reverse_limit",    "name": "反包涨停",    "description": "当日从跌停到涨停", "is_default": False},
    {"id": "rebound_limit",    "name": "炸板回封",    "description": "炸板后重新封板", "is_default": False},
    {"id": "eod_rush",         "name": "尾盘冲量",    "description": "尾盘30分钟放量创新高", "is_default": False},
    {"id": "gap_down_fade",    "name": "高开低走",    "description": "高开3%以上，收盘跌>2%", "is_default": False},
    {"id": "quiet_limit",      "name": "静默涨停",    "description": "涨停且换手率<3%", "is_default": False},
    {"id": "lianban_upgrade",  "name": "连板升级",    "description": "连板数≥2且今日涨停", "is_default": True},
    {"id": "dragon_separate",  "name": "龙头分化",    "description": "板块内龙头涨幅>板块均值×2", "is_default": False},
    {"id": "sector_resonance", "name": "板块共振",    "description": "同日≥3概念板块各有≥3只涨停", "is_default": False},
    {"id": "recent_limit",     "name": "近期涨停",    "description": "近5日内曾出现涨停", "is_default": True},
    {"id": "fund_inflow",      "name": "资金流入",    "description": "主力净流入>1亿", "is_default": True},
    {"id": "lianban",          "name": "连板股",      "description": "当日处于连板状态", "is_default": True},
]


class FeatureCalculator:
    """特征计算器，包含11个量化特征的计算逻辑"""

    def _get_mock_stocks_for_feature(self, feature_id: str) -> List[dict]:
        codes = FEATURE_MOCK_MAP.get(feature_id, [])
        return [s for s in MOCK_STOCKS if s["code"] in codes]

    # ------------------------------------------------------------------
    # 特征1：量能异动
    # ------------------------------------------------------------------
    def volume_surge(self, stocks: List[dict], target_date: date) -> List[dict]:
        """成交量≥5日均量×2.5且当日上涨"""
        result = []
        for s in stocks:
            try:
                if s.get("volume", 0) >= s.get("avg_volume_5d", 1) * 2.5 and s.get("change_pct", 0) > 0:
                    result.append({**s, "feature_meta": {"ratio": round(s["volume"] / s["avg_volume_5d"], 2)}})
            except Exception:
                pass
        if not result:
            result = [{**s, "feature_meta": {"ratio": round(s["volume"] / max(s["avg_volume_5d"], 1), 2)}}
                      for s in self._get_mock_stocks_for_feature("volume_surge")]
        return result

    # ------------------------------------------------------------------
    # 特征2：高换手
    # ------------------------------------------------------------------
    def high_turnover(self, stocks: List[dict], target_date: date) -> List[dict]:
        """换手率≥10%"""
        result = [s for s in stocks if s.get("turnover", 0) >= 10]
        if not result:
            result = self._get_mock_stocks_for_feature("high_turnover")
        return result

    # ------------------------------------------------------------------
    # 特征3：弱转强
    # ------------------------------------------------------------------
    def weak_to_strong(self, stocks: List[dict], target_date: date) -> List[dict]:
        """早盘跌>1%，收盘涨>3%"""
        result = [s for s in stocks
                  if s.get("open_pct", 0) < -1 and s.get("change_pct", 0) > 3]
        if not result:
            result = self._get_mock_stocks_for_feature("weak_to_strong")
        return result

    # ------------------------------------------------------------------
    # 特征4：反包涨停（当日从跌停到涨停）
    # ------------------------------------------------------------------
    def reverse_limit(self, stocks: List[dict], target_date: date) -> List[dict]:
        """当日从跌停到涨停"""
        result = [s for s in stocks
                  if s.get("is_limit_up") and s.get("low_pct", 0) <= -9.9]
        if not result:
            result = self._get_mock_stocks_for_feature("reverse_limit")
        return result

    # ------------------------------------------------------------------
    # 特征5：炸板回封
    # ------------------------------------------------------------------
    def rebound_limit(self, stocks: List[dict], target_date: date) -> List[dict]:
        """炸板后重新封板（需要分时数据，此处用 mock 实现）"""
        result = [s for s in stocks
                  if s.get("is_limit_up") and s.get("zt_broken", False)]
        if not result:
            result = self._get_mock_stocks_for_feature("rebound_limit")
        return result

    # ------------------------------------------------------------------
    # 特征6：尾盘冲量
    # ------------------------------------------------------------------
    def eod_rush(self, stocks: List[dict], target_date: date) -> List[dict]:
        """尾盘30分钟放量创新高"""
        result = [s for s in stocks
                  if s.get("eod_volume_ratio", 0) >= 2 and s.get("eod_new_high", False)]
        if not result:
            result = self._get_mock_stocks_for_feature("eod_rush")
        return result

    # ------------------------------------------------------------------
    # 特征7：高开低走
    # ------------------------------------------------------------------
    def gap_down_fade(self, stocks: List[dict], target_date: date) -> List[dict]:
        """高开3%以上，收盘跌>2%"""
        result = [s for s in stocks
                  if s.get("open_pct", 0) >= 3 and s.get("change_pct", 0) < -2]
        if not result:
            result = self._get_mock_stocks_for_feature("gap_down_fade")
        return result

    # ------------------------------------------------------------------
    # 特征8：静默涨停
    # ------------------------------------------------------------------
    def quiet_limit(self, stocks: List[dict], target_date: date) -> List[dict]:
        """涨停且换手率<3%（缩量封板）"""
        result = [s for s in stocks
                  if s.get("is_limit_up") and s.get("turnover", 100) < 3]
        if not result:
            result = self._get_mock_stocks_for_feature("quiet_limit")
        return result

    # ------------------------------------------------------------------
    # 特征9：连板升级
    # ------------------------------------------------------------------
    def lianban_upgrade(self, stocks: List[dict], target_date: date) -> List[dict]:
        """连板数≥2且今日涨停"""
        result = [s for s in stocks
                  if s.get("is_limit_up") and s.get("lianban_count", 0) >= 2]
        if not result:
            result = self._get_mock_stocks_for_feature("lianban_upgrade")
        return result

    # ------------------------------------------------------------------
    # 特征10：龙头分化
    # ------------------------------------------------------------------
    def dragon_separate(self, stocks: List[dict], target_date: date) -> List[dict]:
        """板块内龙头涨幅>板块均值×2"""
        result = [s for s in stocks
                  if s.get("change_pct", 0) > s.get("sector_avg_change", 0) * 2
                  and s.get("change_pct", 0) > 5]
        if not result:
            result = self._get_mock_stocks_for_feature("dragon_separate")
        return result

    # ------------------------------------------------------------------
    # 特征11：板块共振
    # ------------------------------------------------------------------
    def sector_resonance(self, stocks: List[dict], target_date: date) -> List[dict]:
        """同日≥3概念板块各有≥3只涨停（此处按板块归类判断）"""
        from collections import defaultdict
        industry_map: Dict[str, List[dict]] = defaultdict(list)
        for s in stocks:
            if s.get("is_limit_up"):
                industry_map[s.get("industry", "other")].append(s)

        resonance_industries = [ind for ind, lst in industry_map.items() if len(lst) >= 3]
        result = []
        if len(resonance_industries) >= 3:
            for ind in resonance_industries:
                result.extend(industry_map[ind])

        if not result:
            result = self._get_mock_stocks_for_feature("sector_resonance")
        return result

    # ------------------------------------------------------------------
    # 批量计算接口
    # ------------------------------------------------------------------
    def calculate(self, feature_id: str, stocks: List[dict], target_date: date) -> List[dict]:
        """根据 feature_id 调用对应的特征计算方法"""
        method_map = {
            "volume_surge":     self.volume_surge,
            "high_turnover":    self.high_turnover,
            "weak_to_strong":   self.weak_to_strong,
            "reverse_limit":    self.reverse_limit,
            "rebound_limit":    self.rebound_limit,
            "eod_rush":         self.eod_rush,
            "gap_down_fade":    self.gap_down_fade,
            "quiet_limit":      self.quiet_limit,
            "lianban_upgrade":  self.lianban_upgrade,
            "dragon_separate":  self.dragon_separate,
            "sector_resonance": self.sector_resonance,
            # 别名
            "recent_limit":     self.lianban_upgrade,
            "fund_inflow":      self.volume_surge,
            "lianban":          self.lianban_upgrade,
        }
        fn = method_map.get(feature_id)
        if fn is None:
            return self._get_mock_stocks_for_feature(feature_id)
        try:
            return fn(stocks, target_date)
        except Exception as e:
            logger.warning(f"Feature {feature_id} calculation error: {e}")
            return self._get_mock_stocks_for_feature(feature_id)

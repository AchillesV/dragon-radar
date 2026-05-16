import json
import random
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional

from fastapi import APIRouter, Query, Request
from models import MarketOverview, SectorRank, FundFlowItem, LianbanTier, LianbanStock, DailyAmount

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Mock 数据生成工具
# ---------------------------------------------------------------------------

def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _mock_overview() -> MarketOverview:
    return MarketOverview(
        date=_today_str(),
        rise_count=2341,
        fall_count=985,
        flat_count=120,
        limit_up_count=87,
        limit_down_count=12,
        total_amount=2.87,
        average_turnover=2.34,
        sentiment_index=68.5,
    )


def _mock_sectors(top_n: int = 10) -> List[SectorRank]:
    sectors = [
        SectorRank(name="人工智能", change_pct=4.82, leading_stock="寒武纪", leading_change=10.01,
                   total_amount=856.3, rise_count=48, fall_count=5),
        SectorRank(name="算力租赁", change_pct=3.76, leading_stock="中国长城", leading_change=9.87,
                   total_amount=432.1, rise_count=32, fall_count=3),
        SectorRank(name="量子通信", change_pct=3.21, leading_stock="国盾量子", leading_change=8.54,
                   total_amount=286.5, rise_count=21, fall_count=4),
        SectorRank(name="低空经济", change_pct=2.87, leading_stock="纵横股份", leading_change=7.23,
                   total_amount=312.8, rise_count=28, fall_count=6),
        SectorRank(name="核能概念", change_pct=2.43, leading_stock="中国核电", leading_change=6.12,
                   total_amount=198.4, rise_count=19, fall_count=5),
        SectorRank(name="固态电池", change_pct=1.98, leading_stock="宁德时代", leading_change=4.56,
                   total_amount=567.2, rise_count=35, fall_count=12),
        SectorRank(name="机器人", change_pct=1.54, leading_stock="埃斯顿", leading_change=5.32,
                   total_amount=423.6, rise_count=29, fall_count=10),
        SectorRank(name="半导体材料", change_pct=0.87, leading_stock="雅克科技", leading_change=3.45,
                   total_amount=234.1, rise_count=18, fall_count=14),
        SectorRank(name="光伏设备", change_pct=-0.43, leading_stock="迈为股份", leading_change=1.23,
                   total_amount=189.7, rise_count=12, fall_count=22),
        SectorRank(name="锂矿资源", change_pct=-1.23, leading_stock="盐湖股份", leading_change=-0.56,
                   total_amount=145.3, rise_count=8, fall_count=28),
        SectorRank(name="白酒", change_pct=-1.87, leading_stock="贵州茅台", leading_change=-1.23,
                   total_amount=312.4, rise_count=5, fall_count=35),
        SectorRank(name="医药生物", change_pct=-2.34, leading_stock="药明康德", leading_change=-2.87,
                   total_amount=278.9, rise_count=15, fall_count=42),
    ]
    return sectors[:top_n]


def _mock_fund_flow(top_n: int = 10) -> List[FundFlowItem]:
    items = [
        FundFlowItem(name="人工智能", net_inflow=45.32, main_inflow=52.1, retail_inflow=-6.78, leading_stock="寒武纪"),
        FundFlowItem(name="算力租赁", net_inflow=32.18, main_inflow=38.4, retail_inflow=-6.22, leading_stock="中国长城"),
        FundFlowItem(name="量子通信", net_inflow=28.76, main_inflow=31.2, retail_inflow=-2.44, leading_stock="国盾量子"),
        FundFlowItem(name="低空经济", net_inflow=23.45, main_inflow=27.8, retail_inflow=-4.35, leading_stock="纵横股份"),
        FundFlowItem(name="核能概念", net_inflow=18.92, main_inflow=22.1, retail_inflow=-3.18, leading_stock="中国核电"),
        FundFlowItem(name="白酒", net_inflow=-12.34, main_inflow=-15.6, retail_inflow=3.26, leading_stock="贵州茅台"),
        FundFlowItem(name="医药生物", net_inflow=-18.76, main_inflow=-22.4, retail_inflow=3.64, leading_stock="药明康德"),
        FundFlowItem(name="锂矿资源", net_inflow=-23.45, main_inflow=-27.8, retail_inflow=4.35, leading_stock="盐湖股份"),
        FundFlowItem(name="光伏设备", net_inflow=-28.12, main_inflow=-32.5, retail_inflow=4.38, leading_stock="迈为股份"),
        FundFlowItem(name="房地产", net_inflow=-34.67, main_inflow=-40.2, retail_inflow=5.53, leading_stock="万科A"),
    ]
    return items[:top_n]


def _mock_amount_history() -> List[DailyAmount]:
    result = []
    base_date = datetime.now().date()
    amounts = [
        2.87, 3.12, 2.95, 2.76, 3.08, 2.93, 3.21, 3.05, 2.88, 2.74,
        3.15, 2.98, 3.32, 3.18, 2.91, 2.84, 3.07, 2.96, 3.24, 3.11
    ]
    for i in range(20):
        d = base_date - timedelta(days=i)
        # 跳过周末
        while d.weekday() >= 5:
            d = d - timedelta(days=1)
        result.append(DailyAmount(
            date=d.strftime("%Y-%m-%d"),
            amount=amounts[i],
            change_pct=round(random.uniform(-5, 8), 2),
        ))
    return list(reversed(result))


def _mock_lianban() -> List[LianbanTier]:
    tiers = [
        LianbanTier(count=11, stocks=[
            LianbanStock(code="300XXX", name="某科技", count=11, reason="AI算力", amount=23.4),
        ]),
        LianbanTier(count=8, stocks=[
            LianbanStock(code="002XXX", name="某通信", count=8, reason="量子通信", amount=18.7),
        ]),
        LianbanTier(count=6, stocks=[
            LianbanStock(code="600XXX", name="某能源", count=6, reason="核能", amount=12.3),
            LianbanStock(code="300YYY", name="某机器人", count=6, reason="人形机器人", amount=15.6),
        ]),
        LianbanTier(count=5, stocks=[
            LianbanStock(code="002YYY", name="某低空", count=5, reason="低空经济", amount=9.8),
            LianbanStock(code="603XXX", name="某传媒", count=5, reason="AI+传媒", amount=7.4),
        ]),
        LianbanTier(count=4, stocks=[
            LianbanStock(code="300ZZZ", name="某芯片", count=4, reason="芯片国产化", amount=32.1),
            LianbanStock(code="002ZZZ", name="某医疗", count=4, reason="AI医疗", amount=11.2),
            LianbanStock(code="600YYY", name="某新能源", count=4, reason="固态电池", amount=18.9),
        ]),
        LianbanTier(count=3, stocks=[
            LianbanStock(code="300AAA", name="某软件", count=3, reason="信创", amount=8.7),
            LianbanStock(code="002AAA", name="某材料", count=3, reason="半导体材料", amount=6.3),
            LianbanStock(code="600ZZZ", name="某装备", count=3, reason="军工", amount=14.5),
            LianbanStock(code="300BBB", name="某汽车", count=3, reason="智能驾驶", amount=22.8),
        ]),
    ]
    return tiers


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

def _fetch_legulegu_breadth() -> dict:
    """从乐咕乐股解析涨跌停家数。返回包含 rise_count/fall_count/limit_up_count/limit_down_count 的 dict。"""
    import requests
    from bs4 import BeautifulSoup
    from io import StringIO
    import pandas as pd

    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    r = requests.get("https://legulegu.com/stockdata/market-activity", headers=headers, timeout=10)
    tables = soup_tables = pd.read_html(StringIO(r.text))
    df = soup_tables[0]  # first table has breadth data
    data: dict = {}
    for _, row in df.iterrows():
        for i in range(0, len(row), 2):
            if i + 1 < len(row) and str(row.iloc[i]) not in ("nan", "None"):
                key = str(row.iloc[i]).strip()
                val = row.iloc[i + 1]
                try:
                    data[key] = int(val)
                except (ValueError, TypeError):
                    data[key] = val
    return {
        "rise_count": data.get("上涨", 0),
        "fall_count": data.get("下跌", 0),
        "flat_count": data.get("平盘", 0),
        "limit_up_count": data.get("涨停", 0),
        "limit_down_count": data.get("跌停", 0),
    }


def _fetch_index_amount() -> float:
    """从新浪指数行情获取沪深两市总成交额（万亿元）。"""
    import akshare as ak
    df = ak.stock_zh_index_spot_sina()
    total = 0.0
    # sh000001=上证（沪市合计），sz399106=深证总指（深市合计）
    for code in ("sh000001", "sz399106"):
        row = df[df["代码"] == code]
        if not row.empty:
            total += float(row["成交额"].iloc[0])
    if total == 0:
        total = 2.87e12  # fallback estimate
    return round(total / 1e12, 2)  # 万亿元


@router.get("/overview", response_model=MarketOverview)
async def get_market_overview(request: Request):
    """获取市场概览（上涨/下跌家数、涨跌停、成交额等）"""
    today = _today_str()
    cache_key = f"market:overview:{today}"

    # 尝试从 Redis 读缓存
    try:
        redis = await request.app.state.get_redis()
        if redis:
            cached = await redis.get(cache_key)
            if cached:
                return MarketOverview(**json.loads(cached))
    except Exception as e:
        logger.warning(f"Redis read error: {e}")

    # 尝试从外部数据源获取
    overview = None
    try:
        breadth = _fetch_legulegu_breadth()
        rise = breadth["rise_count"]
        fall = breadth["fall_count"]

        try:
            total_amount = _fetch_index_amount()
        except Exception:
            total_amount = 2.87

        overview = MarketOverview(
            date=today,
            rise_count=rise,
            fall_count=fall,
            flat_count=breadth["flat_count"],
            limit_up_count=breadth["limit_up_count"],
            limit_down_count=breadth["limit_down_count"],
            total_amount=total_amount,
            average_turnover=2.34,
            sentiment_index=round(rise / (rise + fall) * 100 if (rise + fall) > 0 else 50, 1),
        )
    except Exception as e:
        logger.warning(f"market overview fetch error: {e}")

    if overview is None:
        overview = _mock_overview()

    # 写入 Redis 缓存（TTL 60秒）
    try:
        redis = await request.app.state.get_redis()
        if redis:
            await redis.setex(cache_key, 60, overview.model_dump_json())
    except Exception as e:
        logger.warning(f"Redis write error: {e}")

    return overview


@router.get("/sectors", response_model=List[SectorRank])
async def get_sectors(
    type: str = Query("industry", description="板块类型: industry | concept"),
    top_n: int = Query(10, ge=1, le=50),
):
    """获取板块涨跌排名（基于当日涨停池行业热度）"""
    try:
        import akshare as ak
        from collections import defaultdict
        date_str = datetime.now().strftime("%Y%m%d")
        df = ak.stock_zt_pool_em(date=date_str)
        # Actual columns: 代码,名称,涨跌幅,最新价,成交额,流通市值,总市值,换手率,封板资金,首次封板时间,最后封板时间,炸板次数,涨停统计,连板数,所属行业
        if df is not None and not df.empty:
            # Group by industry, rank by limit-up count (proxy for sector heat)
            groups: dict = defaultdict(list)
            for _, row in df.iterrows():
                ind = str(row.get("所属行业", "其他"))
                groups[ind].append(row)

            result = []
            for ind, stocks in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)[:top_n]:
                # Pick lead stock = highest 连板数, then highest 涨跌幅
                lead = sorted(stocks, key=lambda r: (int(r.get("连板数", 1)), float(r.get("涨跌幅", 0))), reverse=True)[0]
                # Approximate sector change_pct = average of member stock change_pcts
                avg_chg = sum(float(r.get("涨跌幅", 0)) for r in stocks) / len(stocks)
                result.append(SectorRank(
                    name=ind,
                    change_pct=round(avg_chg, 2),
                    leading_stock=str(lead.get("名称", "")),
                    leading_change=float(lead.get("涨跌幅", 10.0)),
                    rise_count=len(stocks),
                ))
            if result:
                return result
    except Exception as e:
        logger.warning(f"sectors (zt_pool) error: {e}")

    return _mock_sectors(top_n)


@router.get("/fund_flow", response_model=List[FundFlowItem])
async def get_fund_flow(top_n: int = Query(10, ge=1, le=50)):
    """获取板块资金流向"""
    try:
        import akshare as ak
        df = ak.stock_sector_fund_flow_rank(indicator="今日")
        if df is not None and not df.empty:
            df = df.sort_values("今日净流入额", ascending=False)
            result = []
            for _, row in df.head(top_n).iterrows():
                result.append(FundFlowItem(
                    name=str(row.get("名称", "")),
                    net_inflow=float(row.get("今日净流入额", 0)) / 1e8,
                    main_inflow=float(row.get("今日主力净流入额", 0)) / 1e8,
                    retail_inflow=float(row.get("今日散户净流入额", 0)) / 1e8,
                    leading_stock=str(row.get("今日涨幅最大股", "")),
                ))
            return result
    except Exception as e:
        logger.warning(f"akshare fund_flow error: {e}")

    return _mock_fund_flow(top_n)


@router.get("/amount_history", response_model=List[DailyAmount])
async def get_amount_history():
    """获取近20日市场成交额历史"""
    try:
        import akshare as ak
        df = ak.stock_market_activity_legu()
        if df is not None and not df.empty:
            result = []
            for _, row in df.tail(20).iterrows():
                result.append(DailyAmount(
                    date=str(row.get("日期", "")),
                    amount=float(row.get("成交额", 0)) / 1e12,
                ))
            if result:
                return result
    except Exception as e:
        logger.warning(f"akshare amount_history error: {e}")

    return _mock_amount_history()


@router.get("/lianban", response_model=List[LianbanTier])
async def get_lianban():
    """获取连板梯队信息"""
    try:
        import akshare as ak
        from collections import defaultdict
        date_str = datetime.now().strftime("%Y%m%d")
        df = ak.stock_zt_pool_em(date=date_str)
        # Actual columns: 序号,代码,名称,涨跌幅,最新价,成交额,流通市值,总市值,换手率,封板资金,首次封板时间,最后封板时间,炸板次数,涨停统计,连板数,所属行业
        if df is not None and not df.empty:
            tiers_map = defaultdict(list)
            for _, row in df.iterrows():
                count = int(row.get("连板数", 1))
                amount_raw = row.get("成交额")
                tiers_map[count].append(LianbanStock(
                    code=str(row.get("代码", "")),
                    name=str(row.get("名称", "")),
                    count=count,
                    reason=str(row.get("所属行业", "")),
                    first_limit_time=str(row.get("首次封板时间", "")),
                    amount=round(float(amount_raw) / 1e8, 2) if amount_raw and float(amount_raw) > 0 else None,
                ))
            result = []
            for count in sorted(tiers_map.keys(), reverse=True):
                result.append(LianbanTier(count=count, stocks=tiers_map[count]))
            if result:
                return result
    except Exception as e:
        logger.warning(f"akshare lianban error: {e}")

    return _mock_lianban()

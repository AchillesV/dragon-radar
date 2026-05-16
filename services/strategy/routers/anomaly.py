"""
异动股路由 —— 每种 anomaly_type 对应一类策略特征
所有数据均有贴近真实的 mock fallback
"""
import logging
from typing import List

from fastapi import APIRouter, Path
from models import AnomalyStock

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Mock 数据库
# ---------------------------------------------------------------------------

_MOCK_DATA = {
    "volume_surge": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=9.87, amount=45.6, turnover=12.3,
                     anomaly_type="volume_surge",
                     description="今日成交量达5日均量的3.2倍，主力明显进场，伴随涨停封单。",
                     operation_guide="可在涨停板处挂单排队，止损设昨日收盘价下方2%。关注次日是否高开维持。",
                     score=9.2, industry="电池", lianban_count=2,
                     extra={"volume_ratio": 3.2, "limit_time": "09:45"}),
        AnomalyStock(code="002371", name="北方华创", change_pct=10.01, amount=23.4, turnover=8.7,
                     anomaly_type="volume_surge",
                     description="量能放大2.8倍，半导体设备国产化背景下主力持续加仓。",
                     operation_guide="强势股，可适当追涨，建议分批建仓，总仓位不超过20%。",
                     score=8.8, industry="半导体", lianban_count=3,
                     extra={"volume_ratio": 2.8}),
        AnomalyStock(code="688041", name="海光信息", change_pct=9.95, amount=18.7, turnover=6.5,
                     anomaly_type="volume_surge",
                     description="CPU芯片龙头，量能异动伴随涨停，板块共振明显。",
                     operation_guide="关注能否维持涨停，次日竞价若高开3%以上可跟进。",
                     score=8.5, industry="芯片", lianban_count=1),
    ],
    "weak_to_strong": [
        AnomalyStock(code="002371", name="北方华创", change_pct=7.23, amount=19.8, turnover=7.2,
                     anomaly_type="weak_to_strong",
                     description="早盘低开1.5%后快速拉升，午后强势涨停，弱转强形态标准。",
                     operation_guide="弱转强是主力护盘信号，可在下午2点后放量突破时进场，止损设当日最低价。",
                     score=8.9, industry="半导体"),
        AnomalyStock(code="300015", name="爱尔眼科", change_pct=5.23, amount=8.7, turnover=11.5,
                     anomaly_type="weak_to_strong",
                     description="早盘跌1.2%触及支撑后反转，尾盘收于当日最高区域。",
                     operation_guide="医疗龙头弱转强，关注板块整体情绪，建议小仓位试探。",
                     score=7.6, industry="医疗服务"),
    ],
    "reverse_limit": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=10.02, amount=67.8, turnover=15.4,
                     anomaly_type="reverse_limit",
                     description="今日早盘一度跌停，随后主力强势护盘，尾盘反包涨停，T字板形态。",
                     operation_guide="反包涨停次日大概率高开，可在竞价阶段少量建仓，目标前高或3%-5%空间。",
                     score=9.5, industry="电池", lianban_count=1),
    ],
    "rebound_limit": [
        AnomalyStock(code="688041", name="海光信息", change_pct=9.95, amount=21.3, turnover=7.8,
                     anomaly_type="rebound_limit",
                     description="上午10:30涨停炸板后回落，14:00再次封板，封板资金更大。",
                     operation_guide="炸板回封说明主力意志坚定，建议在第二次封板时少量参与，设3%止损。",
                     score=9.1, industry="芯片"),
    ],
    "eod_rush": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=6.78, amount=38.9, turnover=9.8,
                     anomaly_type="eod_rush",
                     description="14:30后成交量骤增，创当日新高，尾盘买单集中涌入。",
                     operation_guide="尾盘冲量通常预示次日继续高开，可在竞价阶段少量参与，高开3%止盈。",
                     score=8.2, industry="电池"),
        AnomalyStock(code="002371", name="北方华创", change_pct=5.34, amount=15.6, turnover=5.6,
                     anomaly_type="eod_rush",
                     description="尾盘30分钟量能是前4小时均值的2.3倍，股价突破日内高点。",
                     operation_guide="关注次日开盘价，若高开2%以上，可短线持有至前期压力位。",
                     score=7.9, industry="半导体"),
    ],
    "gap_down_fade": [
        AnomalyStock(code="000858", name="五粮液", change_pct=-2.34, amount=43.2, turnover=0.9,
                     anomaly_type="gap_down_fade",
                     description="高开3.5%后持续走弱，尾盘跌幅超过2%，主力出货迹象明显。",
                     operation_guide="高开低走是出货信号，持有者建议止损，空仓者回避，等待企稳后再观察。",
                     score=3.2, industry="白酒"),
        AnomalyStock(code="300059", name="东方财富", change_pct=-1.23, amount=65.4, turnover=3.4,
                     anomaly_type="gap_down_fade",
                     description="跳空高开后量能放大但价格下行，主力借利好出货。",
                     operation_guide="此类形态短期看空，建议观望，若出现缩量企稳可小仓位试探。",
                     score=3.8, industry="互联网金融"),
    ],
    "quiet_limit": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=10.01, amount=12.3, turnover=1.8,
                     anomaly_type="quiet_limit",
                     description="缩量涨停，换手率仅1.8%，主力筹码高度集中，上方供应极少。",
                     operation_guide="缩量涨停后大概率继续上涨，可在次日竞价阶段或开盘后低吸，止损设昨收盘。",
                     score=9.4, industry="电池", lianban_count=4),
    ],
    "lianban_upgrade": [
        AnomalyStock(code="002371", name="北方华创", change_pct=10.01, amount=23.4, turnover=8.7,
                     anomaly_type="lianban_upgrade",
                     description="今日完成第3板，板块情绪高涨，连板高度居市场前列。",
                     operation_guide="3板以上建议控制仓位，可在盘中回踩时少量参与，密切关注板块整体情绪。",
                     score=9.0, industry="半导体", lianban_count=3),
        AnomalyStock(code="688041", name="海光信息", change_pct=9.95, amount=18.7, turnover=6.5,
                     anomaly_type="lianban_upgrade",
                     description="连续第2板，筹码结构良好，短期趋势强劲。",
                     operation_guide="2连板风险相对可控，可在次日竞价低吸，止损设昨日收盘价。",
                     score=8.6, industry="芯片", lianban_count=2),
    ],
    "dragon_separate": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=9.87, amount=45.6, turnover=12.3,
                     anomaly_type="dragon_separate",
                     description="电池板块涨幅均值仅2.1%，宁德时代独涨9.87%，龙头效应显著。",
                     operation_guide="龙头分化说明主力资金高度集中，跟随龙头操作，关注板块内二线是否跟涨。",
                     score=9.3, industry="电池", lianban_count=2),
    ],
    "sector_resonance": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=9.87, amount=45.6, turnover=12.3,
                     anomaly_type="sector_resonance",
                     description="今日人工智能、算力、半导体三大板块共振，各有3只以上涨停，市场情绪极度亢奋。",
                     operation_guide="板块共振行情持续性强，建议顺势操作，可布局各板块龙头，注意高位风险。",
                     score=9.6, industry="电池"),
        AnomalyStock(code="002371", name="北方华创", change_pct=10.01, amount=23.4, turnover=8.7,
                     anomaly_type="sector_resonance",
                     description="半导体板块作为共振主线之一，北方华创作为设备龙头持续强势。",
                     operation_guide="共振行情中选择细分龙头，分散持仓，每只不超过10%仓位。",
                     score=9.2, industry="半导体"),
    ],
    # 前端常用别名
    "recent_limit": [
        AnomalyStock(code="300750", name="宁德时代", change_pct=9.87, amount=45.6, turnover=12.3,
                     anomaly_type="recent_limit",
                     description="近5日内第2次涨停，短线强度持续，主力意图明显。",
                     operation_guide="近期多次涨停说明主力在持续运作，可在回调不破支撑时介入。",
                     score=8.9, industry="电池", lianban_count=2),
        AnomalyStock(code="002371", name="北方华创", change_pct=10.01, amount=23.4, turnover=8.7,
                     anomaly_type="recent_limit",
                     description="近5日第3次涨停，连板升级，强度评级S级。",
                     operation_guide="连续涨停股危险性较高，建议轻仓参与，严格止损。",
                     score=9.1, industry="半导体", lianban_count=3),
        AnomalyStock(code="688041", name="海光信息", change_pct=9.95, amount=18.7, turnover=6.5,
                     anomaly_type="recent_limit",
                     description="5日内完成2次涨停，日均换手适中，筹码结构健康。",
                     operation_guide="可在竞价高开3%以内时跟进，止损设-5%。",
                     score=8.7, industry="芯片", lianban_count=1),
    ],
}

# 为所有未特别定义的 anomaly_type 提供默认 fallback
_DEFAULT_MOCK = _MOCK_DATA["volume_surge"]


@router.get("/anomaly/cards")
async def get_anomaly_cards():
    """返回所有异动类型的卡片摘要（含筛出的股票数量），供首页异动卡片展示。"""
    CARD_META = [
        ("volume_surge",      "放量",     "成交量≥5日均量×2.5且价格上涨"),
        ("high_turnover",     "高换手",   "换手率≥10%或历史90分位"),
        ("weak_to_strong",    "弱转强",   "早盘跌>1%，收盘涨>3%"),
        ("reverse_limit",     "地天板",   "盘中触跌停后收涨停"),
        ("rebound_limit",     "炸板回封", "开板后30min内重新封板"),
        ("eod_rush",          "尾盘抢筹", "14:30后量占全日30%且创新高"),
        ("gap_down_fade",     "高开低走", "高开3%+，收跌2%，全日震幅>5%"),
        ("quiet_limit",       "缩量涨停", "涨停换手率<3%，封单充裕"),
        ("lianban_upgrade",   "连板晋级", "今日涨停且连板数≥2"),
        ("dragon_separate",   "龙头分离", "板块龙头涨幅>板块均值×2"),
        ("sector_resonance",  "板块共振", "≥3板块各有≥3只涨停"),
    ]
    cards = []
    for type_id, title, desc in CARD_META:
        stocks = _MOCK_DATA.get(type_id, _DEFAULT_MOCK)
        cards.append({
            "id": type_id,
            "title": title,
            "description": desc,
            "count": len(stocks),
            "lastUpdated": __import__('datetime').datetime.now().strftime("%H:%M"),
        })
    return cards


@router.get("/anomaly/{anomaly_type}", response_model=List[AnomalyStock])
async def get_anomaly_stocks(anomaly_type: str = Path(..., description="异动类型")):
    """
    获取指定类型的异动股票列表

    支持的类型：volume_surge, weak_to_strong, reverse_limit, rebound_limit,
    eod_rush, gap_down_fade, quiet_limit, lianban_upgrade, dragon_separate,
    sector_resonance, recent_limit
    """
    # 尝试使用实时数据计算
    try:
        from features.calculator import FeatureCalculator, MOCK_STOCKS
        calc = FeatureCalculator()
        today = __import__('datetime').date.today()
        stocks = MOCK_STOCKS  # 实际场景中从数据库或外部接口获取
        matched = calc.calculate(anomaly_type, stocks, today)
        if matched:
            result = []
            for s in matched:
                desc_map = {
                    "volume_surge": f"成交量放大{s.get('feature_meta', {}).get('ratio', 2.5)}倍，量能显著异动。",
                    "weak_to_strong": f"早盘低开{abs(s.get('open_pct', 1)):.1f}%后反转，收盘涨{s['change_pct']:.2f}%。",
                    "lianban_upgrade": f"完成第{s.get('lianban_count', 2)}连板，板块情绪持续高涨。",
                }
                guide_map = {
                    "volume_surge": "量能异动后可在次日竞价低吸，止损设昨日收盘价下方3%。",
                    "weak_to_strong": "弱转强通常有持续性，可小仓位跟进，次日如高开可加仓。",
                    "lianban_upgrade": "连板股注意高位风险，建议轻仓参与，严格执行止损纪律。",
                }
                result.append(AnomalyStock(
                    code=s["code"],
                    name=s["name"],
                    change_pct=s["change_pct"],
                    amount=s.get("amount", 0),
                    turnover=s.get("turnover", 0),
                    anomaly_type=anomaly_type,
                    description=desc_map.get(anomaly_type, f"{anomaly_type} 特征股票"),
                    operation_guide=guide_map.get(anomaly_type, "请结合市场情况谨慎操作。"),
                    score=round(min(9.9, abs(s["change_pct"]) * 0.8 + s.get("turnover", 0) * 0.2), 1),
                    industry=s.get("industry"),
                    lianban_count=s.get("lianban_count"),
                ))
            return result
    except Exception as e:
        logger.warning(f"Feature calculation error for {anomaly_type}: {e}")

    # Fallback：返回预设 mock 数据
    return _MOCK_DATA.get(anomaly_type, _DEFAULT_MOCK)

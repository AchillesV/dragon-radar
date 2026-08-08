"""
科技主线 —— 子板块分类 + 核心票静态数据

分类依据：见 issue WHT-8 用户补充说明。子板块划分/合并沿用用户给出的原始分组，
未做进一步拆分合并。

已按用户要求剔除创业板（300/301开头）和科创板（688开头）股票——分类池
（STOCK_SUBSECTOR_MAP，用于子板块资金流加总）和核心票（CORE_STOCKS）均已剔除。
注意：design_foundry（EDA/IP·晶圆代工/IDM）和 optical_chip（光芯片/硅光）两个
子板块的候选股原本几乎全部集中在科创板，剔除后分类池为空（stock_count=0），
这两个子板块的资金流会一直是 0，核心票列表里也不会出现这两个子板块的股票——
这是过滤规则的直接后果，不是数据缺失，见 issue 评论说明。

CORE_STOCKS（核心票）筛选依据：用户定义"4月到6月底之间涨幅80%以上"，即
2026-04-01（或之后最近交易日）收盘价 -> 2026-06-30（或之前最近交易日）收盘价
累计涨幅 >= 80%（原定 100%，用户后续改为 80%）。已用腾讯 K 线真实历史行情
逐只验证（scripts/compute_core_stocks.py），不是主观拍数。收盘价为不复权价格，
个别除权除息标的的真实涨幅可能略高于计算值。候选池覆盖 137 只股票（16 个子板块，
人工按产业链环节整理，允许同一股票跨子板块），剔除创业板/科创板后剩 48 只，
80% 阈值验证命中 23 只，即为下方 CORE_STOCKS。
"""
from typing import Dict, List, NamedTuple, Tuple


class Subsector(NamedTuple):
    id: str
    name: str
    group: str   # 半导体 / 算力硬件
    hot: bool    # 对应用户标注的 🔥


SUBSECTORS: List[Subsector] = [
    Subsector("storage_chip", "存储芯片", "半导体", True),
    Subsector("digital_chip_design", "数字芯片设计", "半导体", True),
    Subsector("analog_chip", "模拟芯片", "半导体", False),
    Subsector("power_semi", "功率半导体", "半导体", False),
    Subsector("semi_equipment", "半导体设备", "半导体", True),
    Subsector("semi_material", "半导体材料", "半导体", False),
    Subsector("packaging_test", "封装测试", "半导体", True),
    Subsector("design_foundry", "EDA/IP·晶圆代工/IDM", "半导体", False),
    Subsector("optical_module", "光模块", "算力硬件", False),
    Subsector("cpo", "CPO(共封装光学)", "算力硬件", True),
    Subsector("optical_chip", "光芯片/硅光", "算力硬件", False),
    Subsector("copper_connect", "铜连接", "算力硬件", False),
    Subsector("pcb", "PCB/载板", "算力硬件", False),
    Subsector("server", "服务器", "算力硬件", False),
    Subsector("liquid_cooling", "液冷", "算力硬件", True),
    Subsector("network_idc", "交换机/网络设备·IDC数据中心·服务器电源", "算力硬件", False),
]

# 子板块 -> 分类股票池（用于按子板块加总当日主力资金净流入额；已剔除创业板/科创板）
STOCK_SUBSECTOR_MAP: Dict[str, List[Tuple[str, str]]] = {
    "storage_chip": [
        ("603986", "兆易创新"),
        ("001309", "德明利"),
        ("000021", "深科技"),
    ],
    "digital_chip_design": [
        ("603501", "韦尔股份"),
    ],
    "analog_chip": [
        ("600171", "上海贝岭"),
    ],
    "power_semi": [
        ("603290", "斯达半导"),
        ("600460", "士兰微"),
        ("605111", "新洁能"),
        ("600703", "三安光电"),
        ("002617", "露笑科技"),
    ],
    "semi_equipment": [
        ("002371", "北方华创"),
        ("600641", "万业企业"),
        ("603690", "至纯科技"),
    ],
    "semi_material": [
        ("605358", "立昂微"),
        ("002409", "雅克科技"),
        ("603650", "彤程新材"),
        ("600206", "有研新材"),
    ],
    "packaging_test": [
        ("600584", "长电科技"),
        ("002156", "通富微电"),
        ("002185", "华天科技"),
        ("603005", "晶方科技"),
        ("600667", "太极实业"),
    ],
    "design_foundry": [
    ],
    "optical_module": [
        ("002281", "光迅科技"),
        ("000988", "华工科技"),
        ("603083", "剑桥科技"),
    ],
    "cpo": [
        ("002281", "光迅科技"),
    ],
    "optical_chip": [
    ],
    "copper_connect": [
        ("002130", "沃尔核材"),
        ("002897", "意华股份"),
        ("600577", "精达股份"),
        ("002179", "中航光电"),
    ],
    "pcb": [
        ("002463", "沪电股份"),
        ("600183", "生益科技"),
        ("002916", "深南电路"),
        ("603228", "景旺电子"),
        ("002384", "东山精密"),
        ("002436", "兴森科技"),
        ("002815", "崇达技术"),
    ],
    "server": [
        ("601138", "工业富联"),
        ("000977", "浪潮信息"),
        ("603019", "中科曙光"),
        ("000628", "高新发展"),
        ("002261", "拓维信息"),
        ("000034", "神州数码"),
    ],
    "liquid_cooling": [
        ("002837", "英维克"),
    ],
    "network_idc": [
        ("000938", "紫光股份"),
        ("603881", "数据港"),
        ("002335", "科华数据"),
        ("002851", "麦格米特"),
        ("002364", "中恒电气"),
    ],
}

# 核心票 -> 所属子板块（一只股票可能同时属于多个子板块，取第一个作为主展示子板块）
CORE_STOCKS: Dict[str, dict] = {
    "600206": {"name": "有研新材", "subsectors": ['semi_material'], "period_gain_pct": 222.7, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "603986": {"name": "兆易创新", "subsectors": ['storage_chip'], "period_gain_pct": 219.6, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "600667": {"name": "太极实业", "subsectors": ['packaging_test'], "period_gain_pct": 218.2, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "600183": {"name": "生益科技", "subsectors": ['pcb'], "period_gain_pct": 214.7, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "002281": {"name": "光迅科技", "subsectors": ['optical_module', 'cpo'], "period_gain_pct": 195.4, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "002409": {"name": "雅克科技", "subsectors": ['semi_material'], "period_gain_pct": 182.2, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "600584": {"name": "长电科技", "subsectors": ['packaging_test'], "period_gain_pct": 162.2, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "605111": {"name": "新洁能", "subsectors": ['power_semi'], "period_gain_pct": 160.6, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "001309": {"name": "德明利", "subsectors": ['storage_chip'], "period_gain_pct": 153.5, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "002436": {"name": "兴森科技", "subsectors": ['pcb'], "period_gain_pct": 147.1, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "603083": {"name": "剑桥科技", "subsectors": ['optical_module'], "period_gain_pct": 142.2, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "000021": {"name": "深科技", "subsectors": ['storage_chip'], "period_gain_pct": 141.0, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "002384": {"name": "东山精密", "subsectors": ['pcb'], "period_gain_pct": 140.7, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "605358": {"name": "立昂微", "subsectors": ['semi_material'], "period_gain_pct": 132.5, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "600641": {"name": "万业企业", "subsectors": ['semi_equipment'], "period_gain_pct": 113.6, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "600460": {"name": "士兰微", "subsectors": ['power_semi'], "period_gain_pct": 110.3, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "603005": {"name": "晶方科技", "subsectors": ['packaging_test'], "period_gain_pct": 99.4, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "002364": {"name": "中恒电气", "subsectors": ['network_idc'], "period_gain_pct": 99.1, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "002916": {"name": "深南电路", "subsectors": ['pcb'], "period_gain_pct": 98.2, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "002371": {"name": "北方华创", "subsectors": ['semi_equipment'], "period_gain_pct": 96.3, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "603650": {"name": "彤程新材", "subsectors": ['semi_material'], "period_gain_pct": 95.0, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "002463": {"name": "沪电股份", "subsectors": ['pcb'], "period_gain_pct": 92.7, "period_start": "2026-04-01", "period_end": "2026-06-30"},
    "002185": {"name": "华天科技", "subsectors": ['packaging_test'], "period_gain_pct": 87.0, "period_start": "2026-04-01", "period_end": "2026-06-30"},
}

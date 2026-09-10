export interface StockSnapshot {
  code: string;
  name: string;
  market: 'SH' | 'SZ' | 'BJ';
  price: number;
  change: number;
  changePct: number;
  volume: number;
  amount: number;       // 成交额（万元）
  turnoverRate: number;
  pe: number;
  pb: number;
  marketCap: number;    // 亿元
  circMarketCap: number;
  limitUp: boolean;
  limitDown: boolean;
  openPrice: number;
  highPrice: number;
  lowPrice: number;
  prevClose: number;
  date: string;
}

export interface StockRow extends StockSnapshot {
  lianbanCount?: number;
  industry?: string;
  concepts?: string[];
  description?: StockDescription;
  operationGuide?: OperationGuide;
  reportGenerated?: boolean;
  report?: StockReport;
  analysisLoading?: boolean;
}

export interface StockDescription {
  tags: Array<{ text: string; color: string }>;
  summary: string;
  limitUpHistory?: string;
}

export type HighOpenAction = '跟进' | '观察' | '谨慎' | '回避';
export type LowOpenAction = '回避' | '低吸' | '观察' | '谨慎' | '跟进';

export interface OperationGuide {
  highOpen: { action: HighOpenAction; position: string; note: string };
  lowOpen: { action: LowOpenAction; position: string; note: string };
}

export interface StockReport {
  stockCode: string;
  stockName: string;
  generatedAt: string;
  sections: Array<{ title: string; content: string }>;
  scores?: { strength: number; certainty: number; riskRatio: number };
}

export type AnomalyType =
  | 'volume_surge' | 'high_turnover' | 'weak_to_strong'
  | 'reverse_limit' | 'rebound_limit' | 'eod_rush'
  | 'gap_down_fade' | 'quiet_limit' | 'lianban_upgrade'
  | 'dragon_separate' | 'sector_resonance';

export interface AnomalyCard {
  id: AnomalyType;
  title: string;
  description: string;
  icon: string;
  count: number;
  lastUpdated?: string;
}

export interface LianbanTier {
  count: number;
  stocks: Array<{ code: string; name: string; limitUpReason?: string; changePct: number }>;
}

export interface SectorRank {
  name: string;
  changePct: number;
  leadStock?: string;
  leadStockChangePct?: number;
}

export interface FundFlowItem {
  name: string;
  amount: number;  // 亿元，正为净流入，负为净流出
  changePct: number;
}

export interface MarketOverview {
  date: string;
  riseCount: number;
  fallCount: number;
  limitUpCount: number;
  limitDownCount: number;
  totalAmount: number;   // 万亿
  riseCountDelta: number;
  limitUpCountDelta: number;
  maxLianban: { count: number; name: string; code: string };
  marketStatus: 'pre' | 'trading' | 'closed';
  lastUpdated: string;
}

export interface FeatureTag {
  id: string;
  name: string;
  description: string;
  isBuiltin: boolean;
  isDefault: boolean;
}

export interface TrendStock {
  code: string;
  name: string;
  price?: number;
  change?: number;            // 今日涨跌额
  changePct: number;          // 今日涨跌幅（百分比）
  industry?: string;
  breakoutDate: string;        // 放量日 D
  breakoutVolume: number;
  baselineAvgVolume: number;   // 放量前 5 日基准均量
  rangeWindow: '3日' | '5日' | '10日';  // 命中横盘条件的窗口
  rangeChangePct: number;      // 该窗口累计涨跌幅
  description?: string;
  hitCount: number;             // 过去统计周期内的入选次数（不要求连续），>=3 视为持续入选
}

export interface MainlineStock {
  code: string;
  name: string;
  price?: number;
  changePct: number;
  amount?: number;        // 元
  periodGainPct: number;  // 4/1~6/30 累计涨幅
  periodStart?: string;
  periodEnd?: string;
}

// 「趋势 → 分析」板块聚合结果
export interface SectorMember {
  code: string;
  name: string;
  changePct: number;
  isCandidate: boolean;   // 是否来自趋势候选池
  isLead: boolean;        // 是否为本板块候选池领涨股
}

export interface SectorAnalysis {
  code: string;
  name: string;
  type: 'industry' | 'concept';
  score: number;               // 板块热度 0~100
  changePct: number;           // 今日板块涨跌幅
  change5Pct?: number;         // 5 日涨跌幅
  change20Pct?: number;        // 20 日涨跌幅
  lb?: number;                 // 量比
  netInflowPct?: number;       // 今日主力净额 / 成交额（%）
  netInflow5Pct?: number;      // 5 日主力净额 / 成交额（%）
  breadthScore?: number;       // 扩散度 0~100
  upRatio?: number;            // 上涨家数占比 %
  totalCount: number;          // 参与扩散度计算的股票数（并集）
  upCount: number;
  downCount: number;
  strong3Count: number;        // 涨幅 >= 3% 的成分股数
  strong5Count: number;        // 涨幅 >= 5% 的成分股数
  limitUpCount: number;        // 涨停成分股数
  leadStock?: string;
  candidateCount: number;      // 板块内趋势候选股数量
  candidates: SectorMember[];
  signals: string[];           // 策略信号（非买卖结论）
}

export interface TrendAnalysis {
  date: string;
  generatedAt: string;
  candidateCount: number;
  source: string;              // tencent | mock
  sectors: SectorAnalysis[];
}

export interface BulkAnalysisResult {
  date: string;
  totalCandidates: number;
  marketSentiment: 'strong' | 'normal' | 'weak';
  mainTheme: string[];
  sectorRecommendation: Array<{ sector: string; reason: string; keyStocks: string[]; stars: number }>;
  riskWarnings: string[];
  tomorrowFocus: string;
  aiSummary: string;
}

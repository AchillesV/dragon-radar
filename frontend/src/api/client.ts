import axios from 'axios';
import type {
  StockRow,
  AnomalyCard,
  LianbanTier,
  SectorRank,
  FundFlowItem,
  MarketOverview,
  BulkAnalysisResult,
  AnomalyType,
  StockReport,
  StockDescription,
  OperationGuide,
  TrendStock,
  MainlineStock,
  TrendAnalysis,
  TrendScoreComponents,
  LadderStock,
  TrendBacktest,
  BacktestStats,
  BacktestGroup,
  BacktestDateRow,
} from '../types';
import {
  mockStocks,
  mockAnomalyCards,
  mockLianbanTiers,
  mockIndustrySectors,
  mockConceptSectors,
  mockFundFlow,
  mockMarketOverview,
  mockAmountHistory,
  mockBulkAnalysis,
  mockAnomalyStocks,
  mockTrendStocks,
  mockMainlineStocks,
  mockTrendAnalysis,
  mockTrendBacktest,
} from '../mock/data';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
});

function delay(ms = 300): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// 响应转换器：snake_case → camelCase，并补全前端所需字段
// ---------------------------------------------------------------------------

// 行情总览
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toMarketOverview(raw: any): MarketOverview {
  const now = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  const marketStatus: 'pre' | 'trading' | 'closed' =
    (raw.market_status as 'pre' | 'trading' | 'closed') ?? 'closed';

  return {
    date: raw.date ?? new Date().toISOString().slice(0, 10),
    riseCount: raw.rise_count ?? 0,
    fallCount: raw.fall_count ?? 0,
    limitUpCount: raw.limit_up_count ?? 0,
    limitDownCount: raw.limit_down_count ?? 0,
    totalAmount: raw.total_amount ?? 0,
    riseCountDelta: raw.rise_count_delta ?? 0,
    limitUpCountDelta: raw.limit_up_count_delta ?? 0,
    maxLianban: raw.max_lianban ?? { count: 0, name: '--', code: '' },
    marketStatus,
    lastUpdated: now,
  };
}

// 板块涨幅
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toSectorRank(raw: any): SectorRank {
  return {
    name: raw.name,
    changePct: raw.change_pct ?? raw.changePct ?? 0,
    leadStock: raw.leading_stock ?? raw.leadStock,
    leadStockChangePct: raw.leading_change ?? raw.leadStockChangePct,
  };
}

// 资金流向
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toFundFlowItem(raw: any): FundFlowItem {
  return {
    name: raw.name,
    // 后端 net_inflow 已经是亿元，直接使用
    amount: raw.net_inflow ?? raw.amount ?? 0,
    changePct: raw.change_pct ?? raw.changePct ?? 0,
  };
}

// 连板梯队
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toLianbanTier(raw: any): LianbanTier {
  return {
    count: raw.count,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    stocks: (raw.stocks ?? []).map((s: any) => ({
      code: s.code,
      name: s.name,
      limitUpReason: s.reason ?? s.limitUpReason ?? '',
      changePct: s.change_pct ?? s.changePct ?? 10,
    })),
  };
}

// 异动/候选股 → StockRow
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toStockRow(raw: any): StockRow {
  const changePct = raw.change_pct ?? raw.changePct ?? 0;
  const amount = raw.amount ?? 0;          // 后端已是亿元
  const turnoverRate = raw.turnover ?? raw.turnoverRate ?? 0;

  const description: StockDescription | undefined = raw.description
    ? typeof raw.description === 'string'
      ? {
          tags: (raw.matched_features ?? [raw.anomaly_type ?? '']).filter(Boolean).map((f: string) => ({
            text: featureLabel(f),
            color: featureColor(f),
          })),
          summary: raw.description,
          limitUpHistory: raw.lianban_count ? `近期 ${raw.lianban_count} 次涨停` : undefined,
        }
      : raw.description
    : undefined;

  const operationGuide: OperationGuide | undefined = raw.operation_guide
    ? {
        highOpen: { action: '观察', position: '轻仓', note: raw.operation_guide },
        lowOpen: { action: '观察', position: '空仓', note: '低开谨慎操作' },
      }
    : undefined;

  return {
    code: raw.code,
    name: raw.name,
    market: raw.market ?? (raw.code?.startsWith('6') ? 'SH' : 'SZ'),
    price: raw.price ?? raw.close ?? 0,
    change: raw.change ?? 0,
    changePct,
    volume: raw.volume ?? 0,
    amount,
    turnoverRate,
    pe: raw.pe ?? 0,
    pb: raw.pb ?? 0,
    marketCap: raw.market_cap ?? raw.marketCap ?? 0,
    circMarketCap: raw.circ_market_cap ?? raw.circMarketCap ?? 0,
    limitUp: changePct >= 9.9,
    limitDown: changePct <= -9.9,
    openPrice: raw.open_price ?? raw.openPrice ?? 0,
    highPrice: raw.high_price ?? raw.highPrice ?? 0,
    lowPrice: raw.low_price ?? raw.lowPrice ?? 0,
    prevClose: raw.prev_close ?? raw.prevClose ?? 0,
    date: raw.date ?? new Date().toISOString().slice(0, 10),
    lianbanCount: raw.lianban_count ?? raw.lianbanCount,
    industry: raw.industry,
    concepts: raw.concepts ?? (raw.sectors ? raw.sectors : undefined),
    description,
    operationGuide,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toAnomalyCard(raw: any): AnomalyCard {
  return {
    id: raw.id as AnomalyType,
    title: raw.title,
    description: raw.description,
    icon: anomalyIcon(raw.id),
    count: raw.count ?? 0,
    lastUpdated: raw.lastUpdated ?? raw.last_updated,
  };
}

// ---------------------------------------------------------------------------
// 辅助：特征标签文案 & 颜色
// ---------------------------------------------------------------------------
function featureLabel(id: string): string {
  const map: Record<string, string> = {
    recent_limit:    '近期涨停',
    fund_inflow:     '大资金',
    weak_to_strong:  '弱转强',
    quiet_limit:     '缩量涨停',
    lianban:         '连板',
    lianban_upgrade: '连板升级',
    high_turnover:   '高换手',
    volume_surge:    '放量异动',
    rebound_limit:   '炸板回封',
    reverse_limit:   '反包涨停',
    sector_resonance:'板块共振',
    dragon_separate: '龙头分离',
    multi_limit_15d: '多涨停',
    vol_surge_3d:    '近期放量',
    five_day_rally:  '5天连涨',
  };
  return map[id] ?? id;
}
function featureColor(id: string): string {
  const map: Record<string, string> = {
    recent_limit:    'red',
    fund_inflow:     'red',
    weak_to_strong:  'orange',
    quiet_limit:     'purple',
    lianban:         'gold',
    lianban_upgrade: 'gold',
    high_turnover:   'cyan',
    volume_surge:    'red',
    rebound_limit:   'orange',
    reverse_limit:   'magenta',
    sector_resonance:'magenta',
    dragon_separate: 'gold',
    multi_limit_15d: 'volcano',
    vol_surge_3d:    'geekblue',
    five_day_rally:  'green',
  };
  return map[id] ?? 'default';
}
function anomalyIcon(id: string): string {
  const map: Record<string, string> = {
    volume_surge: '📈', high_turnover: '🔄', weak_to_strong: '💪',
    reverse_limit: '🔃', rebound_limit: '🔙', eod_rush: '🌅',
    gap_down_fade: '📉', quiet_limit: '📊', lianban_upgrade: '🏆',
    dragon_separate: '🐉', sector_resonance: '🌊',
  };
  return map[id] ?? '📌';
}

// ---------------------------------------------------------------------------
// API 函数
// ---------------------------------------------------------------------------

// ---- 行情总览 ----
export async function fetchMarketOverview(): Promise<MarketOverview> {
  if (USE_MOCK) { await delay(); return mockMarketOverview; }
  const res = await http.get('/market/overview');
  return toMarketOverview(res.data);
}

// ---- 近20日成交额 ----
export async function fetchAmountHistory(): Promise<Array<{ date: string; amount: number }>> {
  if (USE_MOCK) { await delay(); return mockAmountHistory; }
  // 后端路径用下划线：/market/amount_history
  const res = await http.get<Array<{ date: string; amount: number; change_pct: number }>>('/market/amount_history');
  return res.data.map((d) => ({ date: d.date, amount: d.amount }));
}

// ---- 行业板块涨幅 ----
export async function fetchIndustrySectors(): Promise<SectorRank[]> {
  if (USE_MOCK) { await delay(); return mockIndustrySectors; }
  // 后端：/market/sectors?type=industry
  const res = await http.get('/market/sectors', { params: { type: 'industry', top_n: 10 } });
  return (res.data as unknown[]).map(toSectorRank);
}

// ---- 概念板块涨幅 ----
export async function fetchConceptSectors(): Promise<SectorRank[]> {
  if (USE_MOCK) { await delay(); return mockConceptSectors; }
  // 后端：/market/sectors?type=concept
  const res = await http.get('/market/sectors', { params: { type: 'concept', top_n: 10 } });
  return (res.data as unknown[]).map(toSectorRank);
}

// ---- 板块主力净流入 ----
export async function fetchFundFlow(): Promise<FundFlowItem[]> {
  if (USE_MOCK) { await delay(); return mockFundFlow; }
  // 后端：/market/fund_flow（下划线）
  const res = await http.get('/market/fund_flow', { params: { top_n: 10 } });
  return (res.data as unknown[]).map(toFundFlowItem);
}

// ---- 连板梯队 ----
export async function fetchLianbanTiers(): Promise<LianbanTier[]> {
  if (USE_MOCK) { await delay(); return mockLianbanTiers; }
  const res = await http.get('/market/lianban');
  return (res.data as unknown[]).map(toLianbanTier);
}

// ---- 异动卡片列表（含各类型数量） ----
export async function fetchAnomalyCards(): Promise<AnomalyCard[]> {
  if (USE_MOCK) { await delay(); return mockAnomalyCards; }
  // 后端新增：/anomaly/cards
  const res = await http.get('/anomaly/cards');
  return (res.data as unknown[]).map(toAnomalyCard);
}

// ---- 某类异动的股票列表 ----
export async function fetchAnomalyStocks(type: AnomalyType): Promise<StockRow[]> {
  if (USE_MOCK) { await delay(500); return mockAnomalyStocks[type] ?? []; }
  const res = await http.get(`/anomaly/${type}`);
  return (res.data as unknown[]).map(toStockRow);
}

// ---- 特征筛选候选股 ----
export async function fetchScreeningStocks(features: string[]): Promise<StockRow[]> {
  if (USE_MOCK) { await delay(600); return mockStocks.filter((s) => s.changePct > 0); }
  // 后端：/screening/candidates?feature_ids=xxx,yyy
  const res = await http.get('/screening/candidates', {
    params: { feature_ids: features.join(',') },
  });
  return (res.data as unknown[]).map(toStockRow);
}

// 「趋势」信号
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toTrendStock(raw: any): TrendStock {
  return {
    code: raw.code,
    name: raw.name,
    price: raw.price ?? undefined,
    change: raw.change ?? undefined,
    changePct: raw.change_pct ?? raw.changePct ?? 0,
    industry: raw.industry ?? undefined,
    breakoutDate: raw.breakout_date ?? raw.breakoutDate ?? '',
    breakoutVolume: raw.breakout_volume ?? raw.breakoutVolume ?? 0,
    baselineAvgVolume: raw.baseline_avg_volume ?? raw.baselineAvgVolume ?? 0,
    rangeWindow: raw.range_window ?? raw.rangeWindow ?? '5日',
    rangeChangePct: raw.range_change_pct ?? raw.rangeChangePct ?? 0,
    description: raw.description ?? undefined,
    hitCount: raw.hit_count ?? raw.hitCount ?? 1,
  };
}

export async function fetchTrendStocks(date?: string): Promise<TrendStock[]> {
  if (USE_MOCK) { await delay(500); return mockTrendStocks; }
  // 当天首次扫描时后端会触发全市场逐只扫描，耗时可达数分钟量级，
  // 用独立的较长超时，不影响其他接口的默认 15s 超时；
  // 指定 date 时后端只查本地数据库，正常响应很快，但沿用同一超时以简化调用方
  const res = await http.get('/screening/trend/candidates', {
    timeout: 180000,
    params: date ? { date } : undefined,
  });
  return (res.data as unknown[]).map(toTrendStock);
}

export async function syncTrendStocks(): Promise<TrendStock[]> {
  if (USE_MOCK) { await delay(800); return mockTrendStocks; }
  // 手动同步：强制后端重新全市场扫描当天数据并覆盖数据库，耗时与首次扫描量级一致
  const res = await http.post('/screening/trend/sync', undefined, { timeout: 180000 });
  return (res.data as unknown[]).map(toTrendStock);
}

export async function fetchTrendDates(): Promise<string[]> {
  if (USE_MOCK) { await delay(200); return mockTrendStocks.length ? ['2026-07-31'] : []; }
  const res = await http.get('/screening/trend/dates');
  return res.data as string[];
}

// 「趋势 → 分析」板块聚合
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toTrendAnalysis(raw: any): TrendAnalysis {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const toComponents = (c: any = {}): TrendScoreComponents => ({
    breakoutQuality: c.breakout_quality ?? c.breakoutQuality ?? undefined,
    volumeSustain: c.volume_sustain ?? c.volumeSustain ?? undefined,
    relativeStrength: c.relative_strength ?? c.relativeStrength ?? undefined,
    sectorRelative: c.sector_relative ?? c.sectorRelative ?? undefined,
    sectorResonance: c.sector_resonance ?? c.sectorResonance ?? undefined,
    netInflow: c.net_inflow ?? c.netInflow ?? undefined,
    amount: c.amount ?? undefined,
    attention: c.attention ?? undefined,
    trendIntegrity: c.trend_integrity ?? c.trendIntegrity ?? undefined,
    resilience: c.resilience ?? undefined,
    restart: c.restart ?? undefined,
    newHigh: c.new_high ?? c.newHigh ?? undefined,
    freshness: c.freshness ?? undefined,
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const toLadderStock = (x: any): LadderStock => ({
    code: x.code,
    name: x.name,
    score: x.score ?? 0,
    coreScore: x.core_score ?? x.coreScore ?? 0,
    changePct: x.change_pct ?? x.changePct ?? 0,
    role: x.role ?? '',
  });
  return {
    date: raw.date ?? '',
    generatedAt: raw.generated_at ?? raw.generatedAt ?? '',
    candidateCount: raw.candidate_count ?? raw.candidateCount ?? 0,
    shortlistCount: raw.shortlist_count ?? raw.shortlistCount ?? 0,
    coreCount: raw.core_count ?? raw.coreCount ?? 0,
    finalCount: raw.final_count ?? raw.finalCount ?? 0,
    source: raw.source ?? 'tencent',
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    stocks: (raw.stocks ?? []).map((s: any) => ({
      code: s.code,
      name: s.name,
      price: s.price ?? undefined,
      changePct: s.change_pct ?? s.changePct ?? 0,
      sector: s.sector ?? undefined,
      sectorCode: s.sector_code ?? s.sectorCode ?? undefined,
      sectorType: s.sector_type ?? s.sectorType ?? undefined,
      concept: s.concept ?? undefined,
      conceptCode: s.concept_code ?? s.conceptCode ?? undefined,
      score: s.score ?? 0,
      coreScore: s.core_score ?? s.coreScore ?? 0,
      smartMoneyScore: s.smart_money_score ?? s.smartMoneyScore ?? 0,
      rsScore: s.rs_score ?? s.rsScore ?? 0,
      freshness: s.freshness ?? 0,
      rankInSector: s.rank_in_sector ?? s.rankInSector ?? undefined,
      sectorSize: s.sector_size ?? s.sectorSize ?? undefined,
      ladderRole: s.ladder_role ?? s.ladderRole ?? undefined,
      isCore: s.is_core ?? s.isCore ?? false,
      breakoutDate: s.breakout_date ?? s.breakoutDate ?? undefined,
      breakoutDays: s.breakout_days ?? s.breakoutDays ?? 0,
      lifecycleStage: s.lifecycle_stage ?? s.lifecycleStage ?? 1,
      lifecycleLabel: s.lifecycle_label ?? s.lifecycleLabel ?? '',
      lifecyclePath: s.lifecycle_path ?? s.lifecyclePath ?? [],
      buyStatus: s.buy_status ?? s.buyStatus ?? '',
      buyStatusLabel: s.buy_status_label ?? s.buyStatusLabel ?? '',
      isPick: s.is_pick ?? s.isPick ?? false,
      ret5Pct: s.ret5_pct ?? s.ret5Pct ?? undefined,
      components: toComponents(s.components),
      signals: s.signals ?? [],
    })),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    sectors: (raw.sectors ?? []).map((s: any) => ({
      code: s.code,
      name: s.name,
      type: s.type === 'concept' ? 'concept' : 'industry',
      score: s.score ?? 0,
      changePct: s.change_pct ?? s.changePct ?? 0,
      change5Pct: s.change5_pct ?? s.change5Pct ?? undefined,
      change20Pct: s.change20_pct ?? s.change20Pct ?? undefined,
      lb: s.lb ?? undefined,
      netInflowPct: s.net_inflow_pct ?? s.netInflowPct ?? undefined,
      netInflow5Pct: s.net_inflow5_pct ?? s.netInflow5Pct ?? undefined,
      breadthScore: s.breadth_score ?? s.breadthScore ?? undefined,
      upRatio: s.up_ratio ?? s.upRatio ?? undefined,
      totalCount: s.total_count ?? s.totalCount ?? 0,
      upCount: s.up_count ?? s.upCount ?? 0,
      downCount: s.down_count ?? s.downCount ?? 0,
      strong3Count: s.strong3_count ?? s.strong3Count ?? 0,
      strong5Count: s.strong5_count ?? s.strong5Count ?? 0,
      limitUpCount: s.limit_up_count ?? s.limitUpCount ?? 0,
      leadStock: s.lead_stock ?? s.leadStock ?? undefined,
      candidateCount: s.candidate_count ?? s.candidateCount ?? 0,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ladder: s.ladder
        ? {
            leader: (s.ladder.leader ?? []).map(toLadderStock),
            core: (s.ladder.core ?? []).map(toLadderStock),
            trend: (s.ladder.trend ?? []).map(toLadderStock),
            laggard: (s.ladder.laggard ?? []).map(toLadderStock),
          }
        : undefined,
      ladderScore: s.ladder_score ?? s.ladderScore ?? undefined,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      candidates: (s.candidates ?? []).map((c: any) => ({
        code: c.code,
        name: c.name,
        changePct: c.change_pct ?? c.changePct ?? 0,
        isCandidate: c.is_candidate ?? c.isCandidate ?? true,
        isLead: c.is_lead ?? c.isLead ?? false,
      })),
      signals: s.signals ?? [],
    })),
  };
}

export async function fetchTrendAnalysis(date?: string): Promise<TrendAnalysis> {
  if (USE_MOCK) { await delay(500); return mockTrendAnalysis; }
  // 首次访问时后端会聚合板块（首次拉取板块成分股可能耗时数十秒），用较长超时
  const res = await http.get('/screening/trend/analysis', {
    timeout: 180000,
    params: date ? { date } : undefined,
  });
  return toTrendAnalysis(res.data);
}

// 「趋势 → 分析 → 回测」（Phase 5）
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toBacktestStats(raw: any): BacktestStats {
  return {
    horizon: raw.horizon ?? 0,
    samples: raw.samples ?? 0,
    winRate: raw.win_rate ?? raw.winRate ?? undefined,
    avgRet: raw.avg_ret ?? raw.avgRet ?? undefined,
    medianRet: raw.median_ret ?? raw.medianRet ?? undefined,
    avgWin: raw.avg_win ?? raw.avgWin ?? undefined,
    avgLoss: raw.avg_loss ?? raw.avgLoss ?? undefined,
    payoffRatio: raw.payoff_ratio ?? raw.payoffRatio ?? undefined,
    profitFactor: raw.profit_factor ?? raw.profitFactor ?? undefined,
    expectancy: raw.expectancy ?? undefined,
    maxDrawdown: raw.max_drawdown ?? raw.maxDrawdown ?? undefined,
    best: raw.best ?? undefined,
    worst: raw.worst ?? undefined,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toBacktestGroup(raw: any): BacktestGroup {
  return {
    key: raw.key ?? '',
    label: raw.label ?? raw.key ?? '',
    samples: raw.samples ?? 0,
    winRate: raw.win_rate ?? raw.winRate ?? undefined,
    avgRet5: raw.avg_ret5 ?? raw.avgRet5 ?? undefined,
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toTrendBacktest(raw: any): TrendBacktest {
  return {
    generatedAt: raw.generated_at ?? raw.generatedAt ?? '',
    dateFrom: raw.date_from ?? raw.dateFrom ?? '',
    dateTo: raw.date_to ?? raw.dateTo ?? '',
    sessions: raw.sessions ?? 0,
    universeSize: raw.universe_size ?? raw.universeSize ?? 0,
    signalTotal: raw.signal_total ?? raw.signalTotal ?? 0,
    horizons: raw.horizons ?? [],
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    stats: (raw.stats ?? []).map((s: any) => toBacktestStats(s)),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    byBuyStatus: (raw.by_buy_status ?? raw.byBuyStatus ?? []).map((g: any) => toBacktestGroup(g)),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    byLifecycle: (raw.by_lifecycle ?? raw.byLifecycle ?? []).map((g: any) => toBacktestGroup(g)),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    dates: (raw.dates ?? []).map((d: any): BacktestDateRow => ({
      date: d.date ?? '',
      candidates: d.candidates ?? 0,
      signals: d.signals ?? 0,
      avgRet5: d.avg_ret5 ?? d.avgRet5 ?? undefined,
      winRate5: d.win_rate5 ?? d.winRate5 ?? undefined,
    })),
    source: raw.source ?? 'tencent',
    note: raw.note ?? '',
  };
}

export async function fetchTrendBacktest(sessions?: number): Promise<TrendBacktest> {
  if (USE_MOCK) { await delay(500); return mockTrendBacktest; }
  // 首次访问需拉取数百只日线，冷启动可能数分钟（本地回测快照越多越久）
  const res = await http.get('/screening/trend/backtest', {
    timeout: 600000,
    params: sessions ? { sessions } : undefined,
  });
  return toTrendBacktest(res.data);
}

// 「主线」核心票
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toMainlineStock(raw: any): MainlineStock {
  return {
    code: raw.code,
    name: raw.name,
    price: raw.price ?? undefined,
    changePct: raw.change_pct ?? raw.changePct ?? 0,
    amount: raw.amount ?? undefined,
    periodGainPct: raw.period_gain_pct ?? raw.periodGainPct ?? 0,
    periodStart: raw.period_start ?? raw.periodStart ?? undefined,
    periodEnd: raw.period_end ?? raw.periodEnd ?? undefined,
  };
}

export async function fetchMainlineStocks(): Promise<MainlineStock[]> {
  if (USE_MOCK) { await delay(400); return mockMainlineStocks; }
  const res = await http.get('/screening/mainline/stocks');
  return (res.data as unknown[]).map(toMainlineStock);
}

// ---- 多条件过滤 ----
export async function filterScreeningStocks(
  codes: string[],
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  filters: Record<string, any>,
): Promise<StockRow[]> {
  if (USE_MOCK) { await delay(400); return mockStocks; }
  const res = await http.post('/screening/filter', { codes, filters });
  return (res.data as unknown[]).map(toStockRow);
}

// ---- 单股 AI 分析报告 ----
export async function generateStockReport(code: string, name: string): Promise<StockReport> {
  if (USE_MOCK) {
    await delay(2000);
    const now = new Date().toLocaleString('zh-CN');
    return {
      stockCode: code, stockName: name, generatedAt: now,
      sections: [
        { title: '一、当前形态分析', content: `**${name}（${code}）** 当前处于高位横盘蓄力阶段。\n\n- MA5/MA10/MA20多头排列，均线支撑良好\n- MACD：DIF在DEA上方，动能持续\n- 近日缩量整理，筹码锁定良好\n- 主力成本区间在当前价附近，压力不大` },
        { title: '二、历史相似走势案例', content: `| 历史时段 | 相似度 | 背景 | 后续 | 结果 |\n|---------|-------|------|------|------|\n| 2024-03 涨停板龙头 | 91% | 政策催化 | 回踩5日线后再攻 | +38% |\n| 2023-11 题材共振 | 86% | 板块轮动 | 连续3日放量 | +25% |\n| 2023-07 缩量整理 | 82% | 震荡市 | 突破前高后回调 | -12% |\n\n**规律总结**：相似走势中，2/3概率在突破前高后有20%+的上涨空间。` },
        { title: '三、AI 模式识别', content: `该股当前走势最接近**2024年初宁德时代启动阶段**：放量突破平台→缩量回踩均线→再度放量上攻。\n\n关键验证点：若明日成交量>今日，且收盘在当日高点80%以上，则继续上攻概率极高。` },
        { title: '四、综合评估', content: `- **强势度**：8/10 — 连续涨停，主力意志坚定\n- **确定性**：7/10 — 板块情绪支撑，但高位风险需注意\n- **风险比**：6/10 — 已累积较大涨幅，追高需谨慎` },
        { title: '五、风险提示', content: `⚠️ **高位追涨风险**：当前已累计较大涨幅，追高安全边际低\n\n⚠️ **政策风险**：若利好退潮，题材股回调速度快\n\n⚠️ **大盘风险**：大盘调整时高位股首当其冲\n\n> 本报告由AI生成，仅供参考，不构成投资建议。` },
      ],
      scores: { strength: 80, certainty: 70, riskRatio: 60 },
    };
  }
  // 后端：POST /analysis/stock/{code}
  const res = await http.post<{
    code: string; name: string; date: string; content: string; model: string; from_cache: boolean;
  }>(`/analysis/stock/${code}`, {
    code, name, change_pct: 0, amount: 0, turnover: 0, sectors: [],
  });
  const raw = res.data;
  // 把后端返回的单段 Markdown content 拆成 sections 展示
  return {
    stockCode: raw.code,
    stockName: raw.name,
    generatedAt: raw.date,
    sections: [{ title: 'AI 分析报告', content: raw.content }],
  };
}

// ---- 整体市场分析 ----
export async function fetchBulkAnalysis(codes: string[]): Promise<BulkAnalysisResult> {
  if (USE_MOCK) { await delay(2000); return { ...mockBulkAnalysis, totalCandidates: codes.length }; }
  // 后端：POST /analysis/bulk
  const res = await http.post<{ date: string; content: string; stock_count: number; model: string }>('/analysis/bulk', {
    stock_codes: codes,
    market_data: null,
  });
  const raw = res.data;
  // 把后端 Markdown 内容包装成前端 BulkAnalysisResult 格式
  return {
    date: raw.date,
    totalCandidates: raw.stock_count,
    marketSentiment: 'normal',
    mainTheme: ['AI算力', '特高压', '光通信'],
    sectorRecommendation: [],
    riskWarnings: ['市场高位，注意风险控制'],
    tomorrowFocus: '',
    aiSummary: raw.content,
  };
}

import { useState } from 'react';
import { Button, Drawer, Select, Tag, message } from 'antd';
import { ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import { useTrendAnalysis, useTrendDates, useSyncTrendStocks } from '../../hooks/useTrendData';
import { useIsMobile } from '../../hooks/useIsMobile';
import { useTheme } from '../../hooks/useTheme';
import { COLORS, type RawColors } from '../../constants/colors';
import { LoadingState, EmptyState, ErrorState } from '../common/StatusStates';
import { formatChangePct } from '../../utils/format';
import type { SectorAnalysis, TrendStockScore } from '../../types';
import SectorHeatCard, { starsOf, scoreColor } from './SectorHeatCard';
import CandidateRankCard, { CandidateDetail } from './CandidateRankCard';

const SHOW_STOCKS = 20;

function buildHeatOption(sectors: SectorAnalysis[], c: RawColors) {
  const top = [...sectors].slice(0, 10).sort((a, b) => a.score - b.score);
  return {
    backgroundColor: 'transparent',
    grid: { top: 10, right: 30, bottom: 6, left: 82 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'none' },
      backgroundColor: c.bgHover,
      borderColor: c.borderLight,
      textStyle: { color: c.textPrimary, fontSize: 12 },
      formatter: (params: Array<{ name: string; value: number }>) => {
        const s = top.find((x) => x.name === params[0].name);
        return `<div style="padding:4px 8px"><b>${params[0].name}</b><br/>热度：${params[0].value.toFixed(1)}<br/>
          5日：${s?.change5Pct ?? '--'}% · 扩散：${s?.breadthScore?.toFixed(0) ?? '--'} · 候选 ${s?.candidateCount ?? 0}</div>`;
      },
    },
    xAxis: {
      type: 'value',
      max: 100,
      axisLine: { lineStyle: { color: c.borderLight } },
      splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
      axisLabel: { color: c.textMuted, fontSize: 11 },
    },
    yAxis: {
      type: 'category',
      data: top.map((s) => s.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: c.textSecondary, fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: top.map((s) => ({
          value: Number(s.score.toFixed(1)),
          itemStyle: {
            color: s.score >= 85 ? c.chartRed : s.score >= 70 ? c.chartGold : c.chartBlue,
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barWidth: 14,
        label: { show: true, position: 'right', color: c.textSecondary, fontSize: 11 },
      },
    ],
  };
}

function StatPill({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{
      background: COLORS.bgHover, borderRadius: 6, padding: '8px 10px',
      display: 'flex', flexDirection: 'column', gap: 2, minWidth: 72, flex: 1,
    }}>
      <span style={{ fontSize: 11, color: COLORS.textMuted }}>{label}</span>
      <span style={{ fontSize: 15, fontWeight: 700, color: color ?? COLORS.textPrimary }}>{value}</span>
    </div>
  );
}

function SectorDetail({ sector }: { sector: SectorAnalysis }) {
  const s = starsOf(sector.score);
  const chg = (v?: number) => (v === undefined ? '--' : formatChangePct(v));
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 12 }}>
        <span style={{ fontSize: 20, fontWeight: 800, color: scoreColor(sector.score) }}>
          {sector.score.toFixed(1)}
        </span>
        <span style={{ color: COLORS.chartGold, fontSize: 14 }}>
          {'★'.repeat(s)}{'☆'.repeat(5 - s)}
        </span>
        <Tag color={sector.type === 'concept' ? 'magenta' : 'blue'} style={{ marginInlineStart: 'auto' }}>
          {sector.type === 'concept' ? '概念板块' : '行业板块'}
        </Tag>
      </div>

      <div style={{ fontSize: 12, color: COLORS.textMuted, marginBottom: 6 }}>扩散度（全成分股 ∪ 候选池）</div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
        <StatPill label="上涨占比" value={sector.upRatio === undefined ? '--' : `${sector.upRatio.toFixed(0)}%`} color={COLORS.rise} />
        <StatPill label="上涨/下跌" value={`${sector.upCount}/${sector.downCount}`} />
        <StatPill label="涨幅≥3%" value={`${sector.strong3Count}`} color={COLORS.chartGold} />
        <StatPill label="涨幅≥5%" value={`${sector.strong5Count}`} color={COLORS.chartGold} />
        <StatPill label="涨停" value={`${sector.limitUpCount}`} color={COLORS.limitUp} />
      </div>

      <div style={{ fontSize: 12, color: COLORS.textMuted, marginBottom: 6 }}>量价与资金（腾讯板块级指标）</div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
        <StatPill label="今日" value={chg(sector.changePct)} color={sector.changePct >= 0 ? COLORS.rise : COLORS.fall} />
        <StatPill label="5日涨幅" value={chg(sector.change5Pct)} />
        <StatPill label="20日涨幅" value={chg(sector.change20Pct)} />
        <StatPill label="量比" value={sector.lb === undefined ? '--' : sector.lb.toFixed(2)} />
        <StatPill label="主力净额占比" value={sector.netInflowPct === undefined ? '--' : `${sector.netInflowPct > 0 ? '+' : ''}${sector.netInflowPct.toFixed(1)}%`} color={sector.netInflowPct !== undefined && sector.netInflowPct > 0 ? COLORS.rise : COLORS.fall} />
        <StatPill label="5日净额占比" value={sector.netInflow5Pct === undefined ? '--' : `${sector.netInflow5Pct > 0 ? '+' : ''}${sector.netInflow5Pct.toFixed(1)}%`} color={sector.netInflow5Pct !== undefined && sector.netInflow5Pct > 0 ? COLORS.rise : COLORS.fall} />
      </div>

      {sector.signals.length > 0 && (
        <div style={{ marginBottom: 14, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {sector.signals.map((sig) => <Tag key={sig} color="orange">{sig}</Tag>)}
        </div>
      )}

      <div style={{ fontSize: 12, color: COLORS.textMuted, marginBottom: 6 }}>
        板块内趋势候选股（{sector.candidates.length}）
      </div>
      <div>
        {sector.candidates.map((c) => (
          <div key={c.code} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '8px 10px', borderRadius: 6, background: COLORS.bgHover, marginBottom: 6,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 14, color: COLORS.textPrimary }}>{c.name}</span>
              <span style={{ fontSize: 12, color: COLORS.textMuted }}>{c.code}</span>
              {c.isLead && <Tag color="red" style={{ marginInlineEnd: 0, fontSize: 10 }}>领涨</Tag>}
            </div>
            <span style={{ fontSize: 15, fontWeight: 700, color: c.changePct >= 0 ? COLORS.rise : COLORS.fall }}>
              {formatChangePct(c.changePct)}
            </span>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 14, fontSize: 11, color: COLORS.textMuted, lineHeight: 1.7 }}>
        ⚠️ 以上为策略信号与条件触发指标，不构成买入/卖出建议。扩散度按「板块全成分股（腾讯）∪
        候选池内个股」计算；板块涨跌幅、资金（主力净额/成交额）、量比均来自腾讯板块级指标。
      </div>
    </div>
  );
}

/**
 * 「趋势 → 分析」Tab —— 趋势候选池 → 板块聚合 → 热度 → 量能趋势 → 扩散度
 */
export default function TrendAnalysisView({ selectedDate, onDateChange }: {
  selectedDate?: string;
  onDateChange: (d?: string) => void;
}) {
  const { data, isLoading, isError, refetch } = useTrendAnalysis(selectedDate);
  const { data: dates } = useTrendDates();
  const queryClient = useQueryClient();
  const isMobile = useIsMobile();
  const { rawColors } = useTheme();
  const [refreshing, setRefreshing] = useState(false);
  const [active, setActive] = useState<SectorAnalysis | null>(null);
  const [activeStock, setActiveStock] = useState<TrendStockScore | null>(null);
  const syncMutation = useSyncTrendStocks();

  const isLatest = selectedDate === undefined;

  const handleRefresh = async () => {
    setRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ['trend', 'analysis'] });
    await refetch();
    setRefreshing(false);
  };

  const handleSync = async () => {
    try {
      await syncMutation.mutateAsync();
      await refetch();
      message.success('已同步当天最新数据并重算板块');
    } catch {
      message.error('同步失败，请重试');
    }
  };

  const dateOptions = [
    { value: '', label: '最新' },
    ...(dates ?? []).map((d) => ({ value: d, label: d })),
  ];

  const sectors = data?.sectors ?? [];
  const stocks = data?.stocks ?? [];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'flex-start' : 'center',
          marginBottom: isMobile ? 12 : 20,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div>
          <div style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 4 }}>
            分析
          </div>
          <div style={{ fontSize: 12, color: COLORS.textMuted }}>
            趋势候选池 {data?.candidateCount ?? 0} 只 → 重点板块 {sectors.length} 个
            {stocks.length > 0 && <span> · 重点股 {data?.shortlistCount ?? stocks.length} 只</span>}
            {data?.date && <span> · {data.date}</span>}
            {!isLatest && <span> · 历史：{selectedDate}</span>}
            {data?.source === 'mock' && <span style={{ color: COLORS.chartGold }}> · 数据源异常，展示示例</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Select
            size={isMobile ? 'small' : 'middle'}
            style={{ minWidth: 120 }}
            value={selectedDate ?? ''}
            options={dateOptions}
            onChange={(v) => onDateChange(v === '' ? undefined : v)}
          />
          <Button
            size={isMobile ? 'small' : 'middle'}
            icon={<ReloadOutlined spin={refreshing} />}
            onClick={handleRefresh}
            loading={refreshing}
            style={{ borderColor: COLORS.chartRed, color: COLORS.chartRed, background: 'rgba(255,77,79,0.08)' }}
          >
            {refreshing ? '刷新中...' : '刷新'}
          </Button>
          <Button
            size={isMobile ? 'small' : 'middle'}
            icon={<SyncOutlined spin={syncMutation.isPending} />}
            onClick={handleSync}
            loading={syncMutation.isPending}
            disabled={!isLatest}
            title="重新扫描全市场候选池并重算板块"
          >
            {syncMutation.isPending ? '同步中...' : '同步最新数据'}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <LoadingState height={400} tip="聚合板块并计算热度中（首次约需数十秒）..." />
      ) : isError ? (
        <ErrorState message="板块分析加载失败" onRetry={handleRefresh} />
      ) : sectors.length === 0 ? (
        <EmptyState description="当日候选池暂无可聚合的板块" height={300} />
      ) : (
        <>
          <div style={{
            background: COLORS.bgCard, borderRadius: 8, padding: '12px 12px 4px',
            border: '1px solid var(--c-border)', marginBottom: 16,
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.textSecondary, marginBottom: 4 }}>
              🔥 板块热度 TOP {Math.min(10, sectors.length)}
            </div>
            <ReactECharts
              option={buildHeatOption(sectors, rawColors)}
              style={{ height: Math.max(160, Math.min(10, sectors.length) * 30 + 20) }}
              notMerge
            />
          </div>

          <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.textSecondary, marginBottom: 8 }}>
            今日资金主线（点击查看板块详情）
          </div>
          {sectors.map((s, i) => (
            <SectorHeatCard key={s.code} sector={s} rank={i + 1} onClick={() => setActive(s)} />
          ))}

          {stocks.length > 0 && (
            <>
              <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.textSecondary, margin: '18px 0 8px' }}>
                ⭐ 候选股票 · Smart Money 精选（{data?.shortlistCount ?? stocks.length}）
                <span style={{ color: COLORS.textMuted, fontWeight: 400, fontSize: 12 }}>
                  {' '}· 候选池 {data?.candidateCount ?? 0} → {data?.shortlistCount ?? stocks.length}（点击查看评分）
                </span>
              </div>
              {stocks.slice(0, SHOW_STOCKS).map((st, i) => (
                <CandidateRankCard key={st.code} stock={st} rank={i + 1} onClick={() => setActiveStock(st)} />
              ))}
              {stocks.length > SHOW_STOCKS && (
                <div style={{ fontSize: 12, color: COLORS.textMuted, textAlign: 'center', marginBottom: 8 }}>
                  已展示前 {SHOW_STOCKS} 只，共 {stocks.length} 只重点股
                </div>
              )}
            </>
          )}
        </>
      )}

      <div
        style={{
          marginTop: 20, padding: '12px 16px', background: COLORS.bgCard, borderRadius: 8,
          fontSize: 12, color: COLORS.textMuted, lineHeight: 1.7,
        }}
      >
        💡 <strong style={{ color: COLORS.textSecondary }}>口径说明</strong>：
        板块取自腾讯行业 + 概念板块；「扩散度」按板块全成分股（腾讯）与趋势候选池个股的并集计算，
        综合上涨家数占比、涨幅≥3% 占比与涨停数。板块涨跌幅、资金（主力净额/成交额）、量比全部来自
        腾讯板块级指标（东财接口在生产环境不可用，故不接入）。
        「重点股」在候选池上叠加 Smart Money（放量启动质量 / 量能保持 / 相对强度 / 板块共振 / 资金
        代理 / 缩量回调 / 二次放量 / 新高 / 新鲜度）、相对强度 RS（对标沪深300・中证1000・行业・概念）
        与信号新鲜度，压缩到 50 只。本页仅提供策略信号与条件触发指标，不构成买入/卖出建议。
      </div>

      <Drawer
        placement={isMobile ? 'bottom' : 'right'}
        height={isMobile ? '78vh' : undefined}
        width={isMobile ? undefined : 420}
        open={!!active}
        onClose={() => setActive(null)}
        title={active ? `${active.name} · 板块详情` : ''}
        styles={{ body: { background: COLORS.bgCard }, header: { background: COLORS.bgCard } }}
      >
        {active && <SectorDetail sector={active} />}
      </Drawer>

      <Drawer
        placement={isMobile ? 'bottom' : 'right'}
        height={isMobile ? '78vh' : undefined}
        width={isMobile ? undefined : 420}
        open={!!activeStock}
        onClose={() => setActiveStock(null)}
        title={activeStock ? `${activeStock.name} · ${activeStock.code}` : ''}
        styles={{ body: { background: COLORS.bgCard }, header: { background: COLORS.bgCard } }}
      >
        {activeStock && <CandidateDetail stock={activeStock} />}
      </Drawer>
    </div>
  );
}

import { Button, Card, Select, Table, Tag, Tooltip } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import ReactECharts from 'echarts-for-react';
import { useState } from 'react';
import { useTrendBacktest } from '../../hooks/useTrendData';
import { useIsMobile } from '../../hooks/useIsMobile';
import { COLORS, type RawColors } from '../../constants/colors';
import { useTheme } from '../../hooks/useTheme';
import { LoadingState, ErrorState, EmptyState } from '../common/StatusStates';
import { formatChangePct } from '../../utils/format';
import type { BacktestStats, BacktestGroup, BacktestDateRow } from '../../types';

function retColor(v?: number): string {
  if (v === undefined) return COLORS.textMuted;
  return v > 0 ? COLORS.rise : v < 0 ? COLORS.fall : COLORS.textSecondary;
}

function fmt(v?: number, suffix = ''): string {
  return v === undefined || v === null ? '--' : `${v.toFixed(2)}${suffix}`;
}

function buildRetOption(stats: BacktestStats[], c: RawColors) {
  return {
    backgroundColor: 'transparent',
    grid: { top: 20, right: 20, bottom: 26, left: 46 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: c.bgHover,
      borderColor: c.borderLight,
      textStyle: { color: c.textPrimary, fontSize: 12 },
    },
    xAxis: {
      type: 'category',
      data: stats.map((s) => `T+${s.horizon}`),
      axisLine: { lineStyle: { color: c.borderLight } },
      axisLabel: { color: c.textMuted, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: c.textMuted, fontSize: 11, formatter: '{value}%' },
      splitLine: { lineStyle: { color: c.border, type: 'dashed' } },
    },
    series: [
      {
        type: 'bar',
        barWidth: 26,
        data: stats.map((s) => ({
          value: s.avgRet ?? null,
          itemStyle: {
            color: (s.avgRet ?? 0) >= 0 ? c.rise : c.fall,
            borderRadius: [4, 4, 0, 0],
          },
        })),
        label: {
          show: true, position: 'top', fontSize: 11, color: c.textSecondary,
          formatter: (p: { value: number }) => (p.value === null ? '' : `${p.value}%`),
        },
      },
    ],
  };
}

function StatCard({ s }: { s: BacktestStats }) {
  return (
    <Card size="small" style={{ background: COLORS.bgCard, border: '1px solid var(--c-border)' }}
      styles={{ body: { padding: '10px 12px' } }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: COLORS.textPrimary }}>T+{s.horizon}</span>
        <span style={{ fontSize: 11, color: COLORS.textMuted }}>样本 {s.samples}</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px 10px', fontSize: 12 }}>
        <div><span style={{ color: COLORS.textMuted }}>胜率 </span>
          <span style={{ color: (s.winRate ?? 0) >= 50 ? COLORS.rise : COLORS.textSecondary, fontWeight: 600 }}>{fmt(s.winRate, '%')}</span></div>
        <div><span style={{ color: COLORS.textMuted }}>平均 </span>
          <span style={{ color: retColor(s.avgRet), fontWeight: 600 }}>{fmt(s.avgRet, '%')}</span></div>
        <div><span style={{ color: COLORS.textMuted }}>中位 </span>
          <span style={{ color: retColor(s.medianRet) }}>{fmt(s.medianRet, '%')}</span></div>
        <div><span style={{ color: COLORS.textMuted }}>盈亏比 </span>
          <span style={{ color: COLORS.textPrimary }}>{fmt(s.payoffRatio)}</span></div>
        <div><span style={{ color: COLORS.textMuted }}>PF </span>
          <span style={{ color: COLORS.textPrimary }}>{fmt(s.profitFactor)}</span></div>
        <div><span style={{ color: COLORS.textMuted }}>期望 </span>
          <span style={{ color: retColor(s.expectancy) }}>{fmt(s.expectancy, '%')}</span></div>
        <div><span style={{ color: COLORS.textMuted }}>最大浮亏 </span>
          <span style={{ color: COLORS.fall }}>{fmt(s.maxDrawdown, '%')}</span></div>
        <div><span style={{ color: COLORS.textMuted }}>最好/最差 </span>
          <span style={{ color: COLORS.textSecondary }}>{fmt(s.best)} / {fmt(s.worst)}</span></div>
      </div>
    </Card>
  );
}

function GroupTable({ title, rows, tip }: { title: string; rows: BacktestGroup[]; tip?: string }) {
  const columns = [
    { title: '分组', dataIndex: 'label', key: 'label',
      render: (v: string, r: BacktestGroup) => (
        <span>
          <Tag color="blue" style={{ marginInlineEnd: 6 }}>{v}</Tag>
          <span style={{ fontSize: 11, color: COLORS.textMuted }}>{r.key}</span>
        </span>
      ) },
    { title: '样本', dataIndex: 'samples', key: 'samples', width: 70 },
    { title: '胜率', dataIndex: 'winRate', key: 'winRate', width: 80,
      render: (v?: number) => <span style={{ color: (v ?? 0) >= 50 ? COLORS.rise : COLORS.textSecondary }}>{fmt(v, '%')}</span> },
    { title: 'T+5 平均', dataIndex: 'avgRet5', key: 'avgRet5', width: 90,
      render: (v?: number) => <span style={{ color: retColor(v) }}>{fmt(v, '%')}</span> },
  ];
  return (
    <Card size="small" title={<span style={{ fontSize: 13 }}>{title}{tip && <Tooltip title={tip}><span style={{ color: COLORS.textMuted, marginLeft: 6, cursor: 'help' }}>ⓘ</span></Tooltip>}</span>}
      style={{ background: COLORS.bgCard, border: '1px solid var(--c-border)', marginBottom: 14 }}
      styles={{ body: { padding: 0 } }}>
      <Table<BacktestGroup>
        rowKey="key"
        size="small"
        columns={columns}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: '暂无样本' }}
      />
    </Card>
  );
}

/**
 * 「趋势 → 分析 → 回测」Tab —— Phase 5：T+1/T+3/T+5/T+10 前向收益回测
 */
export default function TrendBacktestView() {
  const [sessions, setSessions] = useState<number>(26);
  const { data, isLoading, isError, refetch } = useTrendBacktest(sessions);
  const queryClient = useQueryClient();
  const isMobile = useIsMobile();
  const { rawColors } = useTheme();
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ['trend', 'backtest'] });
    await refetch();
    setRefreshing(false);
  };

  const stats = data?.stats ?? [];
  const dateColumns = [
    { title: '信号日', dataIndex: 'date', key: 'date' },
    { title: '候选', dataIndex: 'candidates', key: 'candidates', width: 70 },
    { title: '信号', dataIndex: 'signals', key: 'signals', width: 70 },
    { title: 'T+5 胜率', dataIndex: 'winRate5', key: 'winRate5', width: 90,
      render: (v?: number) => <span style={{ color: (v ?? 0) >= 50 ? COLORS.rise : COLORS.textSecondary }}>{fmt(v, '%')}</span> },
    { title: 'T+5 平均', dataIndex: 'avgRet5', key: 'avgRet5', width: 90,
      render: (v?: number) => <span style={{ color: retColor(v) }}>{fmt(v, '%')}</span> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: isMobile ? 'flex-start' : 'center', marginBottom: isMobile ? 12 : 18, flexWrap: 'wrap', gap: 8 }}>
        <div>
          <div style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 4 }}>策略回测</div>
          <div style={{ fontSize: 12, color: COLORS.textMuted }}>
            {data && data.sessions > 0 ? (
              <>
                {data.dateFrom} ~ {data.dateTo} · {data.sessions} 个交易日 · 信号 {data.signalTotal} 笔
                {data.universeSize > 0 && <span> · 覆盖 {data.universeSize} 只</span>}
              </>
            ) : 'T+1 / T+3 / T+5 / T+10 前向收益'}
            {data?.source === 'mock' && <span style={{ color: COLORS.chartGold }}> · 数据源异常，展示示例</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Select
            size={isMobile ? 'small' : 'middle'}
            style={{ minWidth: 130 }}
            value={sessions}
            options={[
              { value: 10, label: '近 10 个交易日' },
              { value: 15, label: '近 15 个交易日' },
              { value: 26, label: '全部（约 26 日）' },
            ]}
            onChange={(v) => setSessions(v)}
          />
          <Button size={isMobile ? 'small' : 'middle'} icon={<ReloadOutlined spin={refreshing} />} onClick={handleRefresh} loading={refreshing}
            style={{ borderColor: COLORS.chartRed, color: COLORS.chartRed, background: 'rgba(255,77,79,0.08)' }}>
            刷新
          </Button>
        </div>
      </div>

      {isLoading ? (
        <LoadingState height={360} tip="回测中：拉取历史日线并计算 T+1/3/5/10 收益（首次约需数十秒）..." />
      ) : isError ? (
        <ErrorState message="回测加载失败" onRetry={handleRefresh} />
      ) : !data || stats.length === 0 ? (
        <EmptyState description="暂无回测数据（本地缺少足够的每日快照）" />
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
            {stats.map((s) => <StatCard key={s.horizon} s={s} />)}
          </div>

          <Card size="small" title={<span style={{ fontSize: 13 }}>各持有周期平均收益</span>}
            style={{ background: COLORS.bgCard, border: '1px solid var(--c-border)', marginBottom: 14 }}
            styles={{ body: { padding: '8px 6px' } }}>
            <ReactECharts option={buildRetOption(stats, rawColors)} style={{ height: 200 }} notMerge />
          </Card>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, 1fr)', gap: 14 }}>
            <GroupTable title="按买点状态（T+5）" rows={data.byBuyStatus} tip="突破确认 / 二次启动 / 缩量回踩 / 趋势运行" />
            <GroupTable title="按生命周期阶段（T+5）" rows={data.byLifecycle} tip="放量启动 / 趋势确认 / 趋势加速 等" />
          </div>

          <Card size="small" title={<span style={{ fontSize: 13 }}>逐日信号表现（T+5）</span>}
            style={{ background: COLORS.bgCard, border: '1px solid var(--c-border)' }}
            styles={{ body: { padding: 0 } }}>
            <Table<BacktestDateRow>
              rowKey="date"
              size="small"
              columns={dateColumns}
              dataSource={data.dates}
              pagination={data.dates.length > 12 ? { pageSize: 12, size: 'small' } : false}
              locale={{ emptyText: '暂无样本' }}
            />
          </Card>
        </>
      )}

      <div style={{ marginTop: 16, padding: '12px 16px', background: COLORS.bgCard, borderRadius: 8, fontSize: 12, color: COLORS.textMuted, lineHeight: 1.7 }}>
        💡 <strong style={{ color: COLORS.textSecondary }}>回测口径</strong>：{data?.note || '对每个交易日 T，仅用截至 T 的量价数据算信号，取买点可关注的前 10 只，统计 T 收盘买入后 T+1/3/5/10 的收益。'}<br />
        胜率为收益 &gt; 0 的样本占比；盈亏比 = 平均盈利 / |平均亏损|；Profit Factor = 盈利总额 / |亏损总额|；
        期望收益 = 胜率 × 平均盈利 + 败率 × 平均亏损。本页仅用于策略验证，不构成买入/卖出建议。
      </div>
    </div>
  );
}

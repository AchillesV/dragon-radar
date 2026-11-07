import { Button, Card, Select, Table, Tag } from 'antd';
import { ReloadOutlined, TrophyOutlined } from '@ant-design/icons';
import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { useQueryClient } from '@tanstack/react-query';
import { useBoardBacktest } from '../../hooks/useBoardData';
import { useIsMobile } from '../../hooks/useIsMobile';
import { useTheme } from '../../hooks/useTheme';
import { COLORS, type RawColors } from '../../constants/colors';
import { LoadingState, EmptyState, ErrorState } from '../common/StatusStates';
import type { BacktestStats, BoardBacktestStock } from '../../types';

function retColor(v?: number): string {
  if (v === undefined || v === null) return COLORS.textMuted;
  return v > 0 ? COLORS.rise : v < 0 ? COLORS.fall : COLORS.textSecondary;
}

function fmt(v?: number): string {
  return v === undefined || v === null ? '—' : `${v.toFixed(2)}%`;
}

function buildRetOption(stats: BacktestStats[], c: RawColors) {
  return {
    backgroundColor: 'transparent',
    grid: { top: 24, right: 20, bottom: 26, left: 46 },
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
          show: true,
          position: 'top',
          fontSize: 11,
          color: c.textSecondary,
          formatter: (p: { value: number }) => (p.value === null ? '' : `${p.value}%`),
        },
      },
    ],
  };
}

function StatCard({ s }: { s: BacktestStats }) {
  const items: Array<[string, string, string]> = [
    ['胜率', fmt(s.winRate), (s.winRate ?? 0) >= 50 ? COLORS.rise : COLORS.textSecondary],
    ['平均', fmt(s.avgRet), retColor(s.avgRet)],
    ['中位', fmt(s.medianRet), retColor(s.medianRet)],
    ['盈亏比', s.payoffRatio !== undefined ? s.payoffRatio.toFixed(2) : '—', COLORS.textPrimary],
    ['PF', s.profitFactor !== undefined ? s.profitFactor.toFixed(2) : '—', COLORS.textPrimary],
    ['最好/最差', `${fmt(s.best)} / ${fmt(s.worst)}`, COLORS.textSecondary],
  ];
  return (
    <Card
      size="small"
      style={{ background: COLORS.bgCard, border: '1px solid var(--c-border)' }}
      styles={{ body: { padding: '10px 12px' } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: COLORS.textPrimary }}>T+{s.horizon}</span>
        <span style={{ fontSize: 11, color: COLORS.textMuted }}>样本 {s.samples}</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px 10px', fontSize: 12 }}>
        {items.map(([label, value, color]) => (
          <div key={label}>
            <span style={{ color: COLORS.textMuted }}>{label} </span>
            <span style={{ color, fontWeight: 600 }}>{value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

/**
 * 「打板 → 回测」Tab —— 对每日最终选出的每只股票做 T+1/T+3/T+5/T+10 前向收益回测
 */
export default function BoardBacktestView() {
  const isMobile = useIsMobile();
  const { rawColors } = useTheme();
  const queryClient = useQueryClient();
  const [days, setDays] = useState(10);
  const { data, isLoading, isError, refetch } = useBoardBacktest(days);
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ['board', 'backtest'] });
    await refetch();
    setRefreshing(false);
  };

  const stats = data?.stats ?? [];
  const stocks = data?.stocks ?? [];
  const hasAnyReturn = stocks.some(
    (s) => s.ret1 !== undefined || s.ret3 !== undefined || s.ret5 !== undefined || s.ret10 !== undefined,
  );

  const columns = [
    { title: '交易日', dataIndex: 'date', key: 'date', width: 105 },
    {
      title: '股票',
      key: 'stock',
      width: 150,
      render: (_: unknown, r: BoardBacktestStock) => (
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: COLORS.textPrimary }}>
            {r.isTop && <TrophyOutlined style={{ color: COLORS.chartGold, marginRight: 4 }} />}
            {r.name}
          </div>
          <div style={{ fontSize: 11, color: COLORS.textMuted }}>{r.code}</div>
        </div>
      ),
    },
    { title: '板块', dataIndex: 'industry', key: 'industry', width: 100,
      render: (v?: string) => <span style={{ color: COLORS.chartBlue, fontSize: 11 }}>{v ?? '—'}</span> },
    { title: '开盘涨幅', dataIndex: 'openPct', key: 'openPct', width: 90,
      render: (v?: number) => <span style={{ color: retColor(v), fontWeight: 600 }}>{fmt(v)}</span> },
    { title: '买入价', dataIndex: 'entry', key: 'entry', width: 85,
      render: (v?: number) => <span style={{ color: COLORS.textSecondary }}>{v !== undefined ? v.toFixed(2) : '—'}</span> },
    { title: 'T+1', dataIndex: 'ret1', key: 'ret1', width: 85,
      render: (v?: number) => <span style={{ color: retColor(v), fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{fmt(v)}</span> },
    { title: 'T+3', dataIndex: 'ret3', key: 'ret3', width: 85,
      render: (v?: number) => <span style={{ color: retColor(v), fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{fmt(v)}</span> },
    { title: 'T+5', dataIndex: 'ret5', key: 'ret5', width: 85,
      render: (v?: number) => <span style={{ color: retColor(v), fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{fmt(v)}</span> },
    { title: 'T+10', dataIndex: 'ret10', key: 'ret10', width: 85,
      render: (v?: number) => <span style={{ color: retColor(v), fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{fmt(v)}</span> },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'flex-start' : 'center',
          marginBottom: isMobile ? 12 : 18,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div>
          <div style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 4 }}>
            打板回测
          </div>
          <div style={{ fontSize: 12, color: COLORS.textMuted }}>
            {data && data.sessions > 0 ? (
              <>
                {data.dateFrom} ~ {data.dateTo} · {data.sessions} 个选股日 · 入选 {data.pickTotal} 只
              </>
            ) : (
              'T 日开盘买入，T+1 / T+3 / T+5 / T+10 收盘卖出'
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Select
            size={isMobile ? 'small' : 'middle'}
            style={{ minWidth: 130 }}
            value={days}
            options={[
              { value: 5, label: '近 5 个选股日' },
              { value: 10, label: '近 10 个选股日' },
            ]}
            onChange={(v) => setDays(v)}
          />
          <Button
            size={isMobile ? 'small' : 'middle'}
            icon={<ReloadOutlined spin={refreshing} />}
            onClick={handleRefresh}
            loading={refreshing}
            style={{ borderColor: COLORS.chartRed, color: COLORS.chartRed, background: 'rgba(255,77,79,0.08)' }}
          >
            刷新
          </Button>
        </div>
      </div>

      {isLoading ? (
        <LoadingState height={320} tip="回测中：拉取历史日线并计算 T+1/3/5/10 收益..." />
      ) : isError ? (
        <ErrorState message="回测加载失败" onRetry={handleRefresh} />
      ) : stocks.length === 0 ? (
        <EmptyState description="暂无回测数据（本地缺少最终选股快照）" height={220} />
      ) : (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
              gap: 10,
              marginBottom: 16,
            }}
          >
            {stats.map((s) => (
              <StatCard key={s.horizon} s={s} />
            ))}
          </div>

          {hasAnyReturn && (
            <Card
              size="small"
              title={<span style={{ fontSize: 13 }}>各持有周期平均收益</span>}
              style={{ background: COLORS.bgCard, border: '1px solid var(--c-border)', marginBottom: 14 }}
              styles={{ body: { padding: '8px 6px' } }}
            >
              <ReactECharts option={buildRetOption(stats, rawColors)} style={{ height: 200 }} notMerge />
            </Card>
          )}

          <Card
            size="small"
            title={<span style={{ fontSize: 13 }}>逐票回测明细</span>}
            style={{ background: COLORS.bgCard, border: '1px solid var(--c-border)' }}
            styles={{ body: { padding: 0 } }}
          >
            <Table<BoardBacktestStock>
              rowKey={(r) => `${r.date}-${r.code}`}
              size="small"
              columns={columns}
              dataSource={stocks}
              scroll={{ x: 900 }}
              pagination={
                stocks.length > 20
                  ? { pageSize: 20, size: 'small', showTotal: (t) => `共 ${t} 只` }
                  : false
              }
              locale={{ emptyText: '暂无样本' }}
            />
          </Card>
          {!hasAnyReturn && (
            <div style={{ marginTop: 10, fontSize: 12, color: COLORS.textMuted }}>
              <Tag color="gold" style={{ marginInlineEnd: 6 }}>待到期</Tag>
              选股日之后的交易日尚不足，T+1/3/5/10 收益会在行情走完后自动补齐。
            </div>
          )}
        </>
      )}

      <div
        style={{
          marginTop: 16,
          padding: '12px 16px',
          background: COLORS.bgCard,
          borderRadius: 8,
          fontSize: 12,
          color: COLORS.textMuted,
          lineHeight: 1.8,
        }}
      >
        <strong style={{ color: COLORS.textSecondary }}>回测口径</strong>
        ：{data?.note || 'T 日开盘买入，T+h 收盘卖出（h = 1/3/5/10 为 T 之后的第 h 个交易日）。'}
        <br />
        胜率为收益 &gt; 0 的样本占比；盈亏比 = 平均盈利 / |平均亏损|；PF = 盈利总额 / |亏损总额|。本页仅用于策略验证，不构成买入/卖出建议。
      </div>
    </div>
  );
}

import { useState } from 'react';
import { Table, Button, Tag, Tooltip } from 'antd';
import type { ColumnType } from 'antd/es/table';
import { ReloadOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import { useTrendStocks } from '../hooks/useTrendData';
import { useIsMobile } from '../hooks/useIsMobile';
import { COLORS } from '../constants/colors';
import { LoadingState, EmptyState, ErrorState } from '../components/common/StatusStates';
import type { TrendStock } from '../types';

function formatVolume(v: number): string {
  if (v >= 100000000) return `${(v / 100000000).toFixed(2)}亿`;
  if (v >= 10000) return `${(v / 10000).toFixed(1)}万`;
  return v.toFixed(0);
}

export default function Trend() {
  const { data: stocks, isLoading, isError, refetch } = useTrendStocks();
  const queryClient = useQueryClient();
  const isMobile = useIsMobile();
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ['trend', 'stocks'] });
    await refetch();
    setRefreshing(false);
  };

  const columns: ColumnType<TrendStock>[] = [
    {
      title: '股票',
      key: 'stock',
      width: 130,
      render: (_: unknown, record: TrendStock) => (
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.textPrimary }}>{record.name}</div>
          <div style={{ fontSize: 11, color: COLORS.textMuted }}>{record.code}</div>
        </div>
      ),
    },
    {
      title: '现价/今日涨跌',
      key: 'price',
      width: 110,
      render: (_: unknown, record: TrendStock) => (
        <div>
          <div style={{ fontVariantNumeric: 'tabular-nums', color: COLORS.textPrimary }}>
            {record.price?.toFixed(2) ?? '-'}
          </div>
          <div style={{ color: record.changePct >= 0 ? COLORS.rise : COLORS.fall, fontSize: 12 }}>
            {record.changePct >= 0 ? '+' : ''}{record.changePct.toFixed(2)}%
          </div>
        </div>
      ),
    },
    {
      title: '放量启动日',
      key: 'breakout',
      width: 160,
      render: (_: unknown, record: TrendStock) => {
        const ratio = record.baselineAvgVolume > 0 ? record.breakoutVolume / record.baselineAvgVolume : 0;
        return (
          <div>
            <div style={{ color: COLORS.textSecondary, fontSize: 12 }}>{record.breakoutDate}</div>
            <Tooltip title={`放量当日成交量 ${formatVolume(record.breakoutVolume)}，放量前5日基准均量 ${formatVolume(record.baselineAvgVolume)}`}>
              <Tag color="volcano" style={{ marginTop: 2 }}>量比 {ratio.toFixed(1)}x</Tag>
            </Tooltip>
          </div>
        );
      },
    },
    {
      title: '横盘 + 资金净流入',
      key: 'fundflow',
      width: 180,
      render: (_: unknown, record: TrendStock) => (
        <div>
          <Tag color="blue">{record.fundFlowWindow}</Tag>
          <div style={{ fontSize: 12, marginTop: 4, color: COLORS.textSecondary }}>
            涨跌幅 {record.fundFlowChangePct >= 0 ? '+' : ''}{record.fundFlowChangePct.toFixed(2)}%
          </div>
          <div style={{ fontSize: 12, color: COLORS.rise }}>
            主力净流入 {record.fundFlowMainInflow.toFixed(2)}亿
          </div>
        </div>
      ),
    },
    {
      title: '说明',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => (
        <span style={{ fontSize: 12, color: COLORS.textMuted }}>{desc ?? '-'}</span>
      ),
    },
  ];

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
            趋势
          </div>
          <div style={{ fontSize: 12, color: COLORS.textMuted }}>
            放量启动 + 持续放量 + 横盘资金净流入 · 命中 {stocks?.length ?? 0} 只
          </div>
        </div>
        <Button
          size={isMobile ? 'small' : 'middle'}
          icon={<ReloadOutlined spin={refreshing} />}
          onClick={handleRefresh}
          loading={refreshing}
          style={{ borderColor: COLORS.chartRed, color: COLORS.chartRed, background: 'rgba(255,77,79,0.08)' }}
        >
          {refreshing ? '刷新中...' : '刷新'}
        </Button>
      </div>

      {isLoading ? (
        <LoadingState height={400} tip="扫描全市场趋势信号中..." />
      ) : isError ? (
        <ErrorState message="趋势信号加载失败" onRetry={handleRefresh} />
      ) : !stocks || stocks.length === 0 ? (
        <EmptyState description="今日暂无符合条件的股票" height={300} />
      ) : (
        <Table<TrendStock>
          columns={columns}
          dataSource={stocks}
          rowKey="code"
          size="small"
          scroll={{ x: 700 }}
          pagination={{ pageSize: 20, showTotal: (total) => `共 ${total} 条` }}
          style={{ background: 'transparent' }}
        />
      )}

      <div
        style={{
          marginTop: 24,
          padding: '12px 16px',
          background: COLORS.bgCard,
          borderRadius: 8,
          fontSize: 12,
          color: COLORS.textMuted,
          lineHeight: 1.7,
        }}
      >
        💡 <strong style={{ color: COLORS.textSecondary }}>规则说明</strong>：
        近10个交易日内某天成交量 ≥ 前5日均量 2.5 倍视为放量启动，此后每日成交量需维持在基准均量 1.5 倍以上；
        同时最近 3/5/10 日中任意一个窗口需同时满足涨跌幅在 -10%~10% 之间且主力资金净流入为正。
        剔除创业板（300/301开头）和 ST 股票。数据每 10 分钟刷新一次。
      </div>
    </div>
  );
}

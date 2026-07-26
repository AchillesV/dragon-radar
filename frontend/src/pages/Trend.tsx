import { useState } from 'react';
import { Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import { useTrendStocks } from '../hooks/useTrendData';
import { useIsMobile } from '../hooks/useIsMobile';
import { COLORS } from '../constants/colors';
import { LoadingState, EmptyState, ErrorState } from '../components/common/StatusStates';
import StockTable from '../components/screening/StockTable';

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
            放量启动 + 持续放量 + 横盘 · 命中 {stocks?.length ?? 0} 只
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
        <StockTable
          stocks={stocks}
          mode="trend"
          loading={false}
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
        同时最近 3/5/10 日中任意一个窗口累计涨跌幅需在 -10%~10% 之间（横盘）。
        剔除创业板（300/301开头）和 ST 股票。全市场逐只扫描，首次加载可能需要一分钟左右，结果缓存 30 分钟。
      </div>
    </div>
  );
}

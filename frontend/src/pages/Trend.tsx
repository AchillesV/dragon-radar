import { useState } from 'react';
import { Button, Select, message } from 'antd';
import { ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import { useTrendStocks, useTrendDates, useSyncTrendStocks } from '../hooks/useTrendData';
import { useIsMobile } from '../hooks/useIsMobile';
import { COLORS } from '../constants/colors';
import { LoadingState, EmptyState, ErrorState } from '../components/common/StatusStates';
import StockTable from '../components/screening/StockTable';

export default function Trend() {
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined);
  const { data: dates } = useTrendDates();
  const { data: stocks, isLoading, isError, refetch } = useTrendStocks(selectedDate);
  const queryClient = useQueryClient();
  const isMobile = useIsMobile();
  const [refreshing, setRefreshing] = useState(false);
  const syncMutation = useSyncTrendStocks();

  const isLatest = selectedDate === undefined;

  const handleRefresh = async () => {
    setRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ['trend', 'stocks'] });
    await queryClient.invalidateQueries({ queryKey: ['trend', 'dates'] });
    await refetch();
    setRefreshing(false);
  };

  const handleSync = async () => {
    try {
      await syncMutation.mutateAsync();
      message.success('已同步当天最新数据');
    } catch {
      message.error('同步失败，请重试');
    }
  };

  const dateOptions = [
    { value: '', label: '最新' },
    ...(dates ?? []).map((d) => ({ value: d, label: d })),
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
            放量启动 + 持续放量 + 横盘 · 命中 {stocks?.length ?? 0} 只
            {!isLatest && <span> · 查看历史：{selectedDate}</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Select
            size={isMobile ? 'small' : 'middle'}
            style={{ minWidth: 120 }}
            value={selectedDate ?? ''}
            options={dateOptions}
            onChange={(v) => setSelectedDate(v === '' ? undefined : v)}
          />
          <Button
            size={isMobile ? 'small' : 'middle'}
            icon={<ReloadOutlined spin={refreshing} />}
            onClick={handleRefresh}
            loading={refreshing}
            disabled={!isLatest}
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
            title="重新扫描全市场并覆盖数据库中当天的数据"
          >
            {syncMutation.isPending ? '同步中...' : '同步最新数据'}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <LoadingState height={400} tip={isLatest ? '扫描全市场趋势信号中...' : '加载历史数据中...'} />
      ) : isError ? (
        <ErrorState message="趋势信号加载失败" onRetry={handleRefresh} />
      ) : !stocks || stocks.length === 0 ? (
        <EmptyState description={isLatest ? '今日暂无符合条件的股票' : '当天暂无符合条件的股票'} height={300} />
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
        剔除创业板（300/301开头）和 ST 股票。每个交易日首次加载会全市场逐只扫描并保存到本地，同一天内再次访问直接读取，仅当天无数据时才重新扫描；
        可点击「同步最新数据」随时手动重新扫描当天全市场数据并覆盖本地已保存的当天数据。
        可通过右上角下拉框查看近10个交易日的历史结果。列表按近10个交易日统计周期内的入选次数从高到低排序，入选 3 次及以上（不要求连续）的股票会在名称旁标注「N次入选」；可点击表格上方「复制入选」一键复制这些多次入选的股票。
      </div>
    </div>
  );
}

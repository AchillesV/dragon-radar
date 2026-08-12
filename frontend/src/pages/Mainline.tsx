import { useMainlineStocks } from '../hooks/useMainlineData';
import { useIsMobile } from '../hooks/useIsMobile';
import { COLORS } from '../constants/colors';
import { LoadingState, EmptyState, ErrorState } from '../components/common/StatusStates';
import MainlineStockTable from '../components/mainline/MainlineStockTable';

export default function Mainline() {
  const { data: stocks, isLoading: stocksLoading, isError, refetch } = useMainlineStocks();
  const isMobile = useIsMobile();

  return (
    <div>
      <div style={{ marginBottom: isMobile ? 12 : 20 }}>
        <div style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 4 }}>
          主线
        </div>
        <div style={{ fontSize: 12, color: COLORS.textMuted }}>
          主力核心票（2026-04-01~2026-06-30 累计涨幅≥80%，全市场逐只验证，已剔除创业板/科创板/ST）
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.textPrimary }}>
          主力核心票 {stocks ? `（${stocks.length} 只）` : ''}
        </div>
      </div>

      {stocksLoading ? (
        <LoadingState height={300} />
      ) : isError ? (
        <ErrorState message="核心票列表加载失败" onRetry={refetch} />
      ) : !stocks || stocks.length === 0 ? (
        <EmptyState description="暂无核心票" height={300} />
      ) : (
        <MainlineStockTable stocks={stocks} loading={false} />
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
        💡 <strong style={{ color: COLORS.textSecondary }}>说明</strong>：
        「核心票」定义为 2026-04-01 至 2026-06-30 期间累计涨幅≥80% 的股票，全市场逐只用真实历史行情验证，
        不再限定候选板块或行业——已剔除创业板（300/301开头）、科创板（688开头）和 ST 股票。
      </div>
    </div>
  );
}

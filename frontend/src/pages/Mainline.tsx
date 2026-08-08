import { useMemo, useState } from 'react';
import { Select } from 'antd';
import { useMainlineSectors, useMainlineStocks } from '../hooks/useMainlineData';
import { useTheme } from '../hooks/useTheme';
import { useIsMobile } from '../hooks/useIsMobile';
import { COLORS } from '../constants/colors';
import { LoadingState, EmptyState, ErrorState } from '../components/common/StatusStates';
import MainlineFlowChart from '../components/mainline/MainlineFlowChart';
import MainlineStockTable from '../components/mainline/MainlineStockTable';

export default function Mainline() {
  const [subsector, setSubsector] = useState<string | undefined>(undefined);
  const { data: sectors, isLoading: sectorsLoading } = useMainlineSectors();
  const { data: stocks, isLoading: stocksLoading, isError, refetch } = useMainlineStocks(subsector);
  const { rawColors } = useTheme();
  const isMobile = useIsMobile();

  const subsectorOptions = useMemo(
    () => [
      { value: '', label: '全部子板块' },
      ...(sectors ?? []).map((s) => ({ value: s.id, label: `${s.hot ? '🔥 ' : ''}${s.name}` })),
    ],
    [sectors],
  );

  return (
    <div>
      <div style={{ marginBottom: isMobile ? 12 : 20 }}>
        <div style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 4 }}>
          主线
        </div>
        <div style={{ fontSize: 12, color: COLORS.textMuted }}>
          科技主线 16 个子板块资金流 · 核心票（2026-04-01~2026-06-30 累计涨幅翻倍）
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <MainlineFlowChart data={sectors ?? []} loading={sectorsLoading} rawColors={rawColors} />
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
          科技主线核心票 {stocks ? `（${stocks.length} 只）` : ''}
        </div>
        <Select
          size={isMobile ? 'small' : 'middle'}
          style={{ minWidth: 200 }}
          value={subsector ?? ''}
          options={subsectorOptions}
          onChange={(v) => setSubsector(v === '' ? undefined : v)}
          showSearch
          filterOption={(input, option) =>
            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
          }
        />
      </div>

      {stocksLoading ? (
        <LoadingState height={300} />
      ) : isError ? (
        <ErrorState message="核心票列表加载失败" onRetry={refetch} />
      ) : !stocks || stocks.length === 0 ? (
        <EmptyState description="该子板块暂无核心票" height={300} />
      ) : (
        <MainlineStockTable stocks={stocks} sectors={sectors ?? []} loading={false} />
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
        「核心票」定义为 2026-04-01 至 2026-06-30 期间累计涨幅翻倍（≥100%）的科技股，已用真实历史行情逐只验证；
        子板块划分覆盖半导体、算力硬件（AI服务器/光通信）两条产业链共 16 个子板块，同一股票可能同时属于多个子板块。
        子板块「主力资金净流入」= 该子板块分类股票池内所有股票当日主力净流入额相加，数据源为东财个股资金流向接口，
        该接口在部分网络环境下不稳定，取数失败的股票会被跳过而非计为 0；若某子板块下所有股票均取数失败，
        对应净流入会显示为 0 并在图表上方提示。本板块不剔除创业板/科创板股票（与「异动监控」「特征筛选」规则不同），
        仍剔除 ST 股票。
      </div>
    </div>
  );
}

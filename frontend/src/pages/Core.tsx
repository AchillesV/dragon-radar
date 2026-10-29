import { useState } from 'react';
import { useCoreResult } from '../hooks/useCoreData';
import { useIsMobile } from '../hooks/useIsMobile';
import { COLORS } from '../constants/colors';
import { LoadingState, EmptyState, ErrorState } from '../components/common/StatusStates';
import CoreSectorCards from '../components/core/CoreSectorCards';
import CoreStockTable from '../components/core/CoreStockTable';

export default function Core() {
  const { data, isLoading, isError, refetch } = useCoreResult();
  const isMobile = useIsMobile();
  const [selected, setSelected] = useState<string | null>(null);

  const sectors = data?.sectors ?? [];
  const watchlist = data?.watchlist ?? [];
  const stocks = (data?.stocks ?? []).filter((s) => !selected || s.sector === selected);

  return (
    <div>
      <div style={{ marginBottom: isMobile ? 12 : 20 }}>
        <div style={{ fontSize: isMobile ? 16 : 20, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 4 }}>
          核心
        </div>
        <div style={{ fontSize: 12, color: COLORS.textMuted, lineHeight: 1.7 }}>
          热门板块内的首板票（放量 + 资金净流入 + 涨停扩散 + 最高板），二板及以上不追
        </div>
        {data && (
          <div style={{ fontSize: 12, color: COLORS.textMuted, marginTop: 6 }}>
            交易日 {data.date} · 更新于 {data.generatedAt} · 全市场最高 {data.marketMaxBoard} 板
          </div>
        )}
      </div>

      {data?.dataQuality === 'partial' && (
        <div
          style={{
            marginBottom: 12,
            padding: '8px 12px',
            background: 'rgba(250,173,20,0.1)',
            border: '1px solid rgba(250,173,20,0.3)',
            borderRadius: 6,
            fontSize: 12,
            color: COLORS.chartGold,
          }}
        >
          部分板块的同花顺资金/放量数据缺失，相关条件按「未知」放行，请谨慎参考。
        </div>
      )}

      {isLoading ? (
        <LoadingState height={300} tip="正在聚合涨停池与板块资金数据..." />
      ) : isError ? (
        <ErrorState message="核心数据加载失败" onRetry={refetch} />
      ) : (
        <>
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
              热门板块 {sectors.length > 0 ? `（${sectors.length} 个）` : ''}
            </div>
            {selected && (
              <div
                onClick={() => setSelected(null)}
                style={{
                  fontSize: 12,
                  color: COLORS.chartBlue,
                  cursor: 'pointer',
                  padding: '2px 8px',
                  border: '1px solid rgba(24,144,255,0.35)',
                  borderRadius: 4,
                }}
              >
                已选：{selected} ✕
              </div>
            )}
          </div>

          {sectors.length === 0 ? (
            <EmptyState
              description={
                watchlist.length > 0
                  ? `今日没有完全达标的热门板块，${watchlist.length} 个板块进入观察池`
                  : '今日没有同时满足 放量≥1.3x / 5日资金净流入 / 涨停扩散 / 高度 的板块'
              }
              height={180}
            />
          ) : (
            <CoreSectorCards sectors={sectors} selected={selected} onSelect={setSelected} isMobile={isMobile} />
          )}

          {watchlist.length > 0 && (
            <>
              <div style={{ marginTop: 24, marginBottom: 12, fontSize: 14, fontWeight: 600, color: COLORS.textSecondary }}>
                观察池（扩散 + 高度已达标，资金或放量未达标）
              </div>
              <CoreSectorCards
                sectors={watchlist}
                selected={null}
                onSelect={() => setSelected(null)}
                isMobile={isMobile}
                variant="watch"
              />
            </>
          )}

          <div style={{ marginTop: 24, marginBottom: 12, fontSize: 14, fontWeight: 600, color: COLORS.textPrimary }}>
            首板候选 {stocks.length > 0 ? `（${stocks.length} 只）` : ''}
          </div>

          {stocks.length === 0 ? (
            <EmptyState description="达标板块内暂无首板票" height={180} />
          ) : (
            <CoreStockTable stocks={stocks} loading={false} />
          )}
        </>
      )}

      <div
        style={{
          marginTop: 24,
          padding: '12px 16px',
          background: COLORS.bgCard,
          borderRadius: 8,
          fontSize: 12,
          color: COLORS.textMuted,
          lineHeight: 1.8,
        }}
      >
        <strong style={{ color: COLORS.textSecondary }}>筛选规则</strong>
        ：热门板块需满足 ① 近3日板块成交额 / 前20日均值 ≥ 1.3；② 5日资金净额与今日净额均为正；
        ③ 涨停 ≥ 3 家（或 ≥ 2 家且板块上涨占比 ≥ 65%）；④ 板块最高板 = 全市场最高板，或连板（≥2板）家数 ≥ 2。
        板块内取「连板数 = 1」的股票，已剔除创业板（300/301）、科创板（688）与 ST。
        板块资金/成交额来自同花顺（数据缺失时标注为「未知」），涨停池来自东财。
      </div>
    </div>
  );
}

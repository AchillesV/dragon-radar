import { useEffect, useState } from 'react';
import FeatureSelector from '../components/screening/FeatureSelector';
import FilterBar, { FilterValues } from '../components/screening/FilterBar';
import StockTable from '../components/screening/StockTable';
import { useScreeningStocks } from '../hooks/useScreeningData';
import { COLORS } from '../constants/colors';
import { LoadingState } from '../components/common/StatusStates';
import type { StockRow } from '../types';

export default function Screening() {
  const { data, isLoading, isFetching } = useScreeningStocks();
  const [filteredStocks, setFilteredStocks] = useState<StockRow[]>([]);

  useEffect(() => {
    if (data) {
      setFilteredStocks(data);
    }
  }, [data]);

  const handleFilterChange = (filters: FilterValues) => {
    if (!data) return;
    let result = [...data];

    if (Array.isArray(filters.market) && filters.market.length > 0) {
      result = result.filter((s) => (filters.market as string[]).includes(s.market));
    }
    if (Array.isArray(filters.industry) && filters.industry.length > 0) {
      result = result.filter((s) => (filters.industry as string[]).includes(s.industry ?? ''));
    }
    if (typeof filters.changePctMin === 'number') {
      result = result.filter((s) => s.changePct >= (filters.changePctMin as number));
    }
    if (typeof filters.changePctMax === 'number') {
      result = result.filter((s) => s.changePct <= (filters.changePctMax as number));
    }
    if (typeof filters.amountMin === 'number') {
      const minAmount = (filters.amountMin as number) * 10000;
      result = result.filter((s) => s.amount >= minAmount);
    }
    if (typeof filters.turnoverMin === 'number') {
      result = result.filter((s) => s.turnoverRate >= (filters.turnoverMin as number));
    }
    if (typeof filters.lianbanMin === 'number') {
      result = result.filter((s) => (s.lianbanCount ?? 0) >= (filters.lianbanMin as number));
    }
    setFilteredStocks(result);
  };

  return (
    <div>
      {/* Page title */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.textPrimary, marginBottom: 4 }}>
          特征筛选
        </div>
        <div style={{ fontSize: 13, color: COLORS.textMuted }}>
          基于多维特征组合筛选强势股票，智能分析操作建议
        </div>
      </div>

      {/* Feature selector */}
      <FeatureSelector />

      {/* Filter bar */}
      <FilterBar onChange={handleFilterChange} />

      {/* Stock table */}
      {isLoading ? (
        <LoadingState height={300} tip="筛选中..." />
      ) : (
        <StockTable
          stocks={filteredStocks}
          loading={isFetching && !isLoading}
          mode="screening"
          showOperationGuide={true}
        />
      )}
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchTrendStocks, fetchTrendDates, syncTrendStocks, fetchTrendAnalysis, fetchTrendBacktest } from '../api/client';

export function useTrendStocks(date?: string) {
  return useQuery({
    queryKey: ['trend', 'stocks', date ?? 'latest'],
    queryFn: () => fetchTrendStocks(date),
    staleTime: 5 * 60 * 1000,
  });
}

export function useTrendDates() {
  return useQuery({
    queryKey: ['trend', 'dates'],
    queryFn: fetchTrendDates,
    staleTime: 5 * 60 * 1000,
  });
}

// 「趋势 → 分析」板块聚合
export function useTrendAnalysis(date?: string) {
  return useQuery({
    queryKey: ['trend', 'analysis', date ?? 'latest'],
    queryFn: () => fetchTrendAnalysis(date),
    staleTime: 5 * 60 * 1000,
  });
}

// 「趋势 → 分析 → 回测」（Phase 5）
export function useTrendBacktest(sessions?: number) {
  return useQuery({
    queryKey: ['trend', 'backtest', sessions ?? 'default'],
    queryFn: () => fetchTrendBacktest(sessions),
    staleTime: 30 * 60 * 1000,
  });
}

export function useSyncTrendStocks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: syncTrendStocks,
    onSuccess: (stocks) => {
      queryClient.setQueryData(['trend', 'stocks', 'latest'], stocks);
      queryClient.invalidateQueries({ queryKey: ['trend', 'dates'] });
      // 候选池刷新后，板块分析需重算
      queryClient.invalidateQueries({ queryKey: ['trend', 'analysis'] });
    },
  });
}

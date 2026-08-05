import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchTrendStocks, fetchTrendDates, syncTrendStocks } from '../api/client';

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

export function useSyncTrendStocks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: syncTrendStocks,
    onSuccess: (stocks) => {
      queryClient.setQueryData(['trend', 'stocks', 'latest'], stocks);
      queryClient.invalidateQueries({ queryKey: ['trend', 'dates'] });
    },
  });
}

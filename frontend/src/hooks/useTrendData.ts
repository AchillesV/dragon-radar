import { useQuery } from '@tanstack/react-query';
import { fetchTrendStocks } from '../api/client';

export function useTrendStocks() {
  return useQuery({
    queryKey: ['trend', 'stocks'],
    queryFn: fetchTrendStocks,
    staleTime: 5 * 60 * 1000,
  });
}

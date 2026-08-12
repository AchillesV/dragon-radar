import { useQuery } from '@tanstack/react-query';
import { fetchMainlineStocks } from '../api/client';

export function useMainlineStocks() {
  return useQuery({
    queryKey: ['mainline', 'stocks'],
    queryFn: fetchMainlineStocks,
    staleTime: 5 * 60 * 1000,
  });
}

import { useQuery } from '@tanstack/react-query';
import { fetchMainlineSectors, fetchMainlineStocks } from '../api/client';

export function useMainlineSectors() {
  return useQuery({
    queryKey: ['mainline', 'sectors'],
    queryFn: fetchMainlineSectors,
    staleTime: 60 * 1000,
  });
}

export function useMainlineStocks(subsector?: string) {
  return useQuery({
    queryKey: ['mainline', 'stocks', subsector ?? 'all'],
    queryFn: () => fetchMainlineStocks(subsector),
    staleTime: 5 * 60 * 1000,
  });
}

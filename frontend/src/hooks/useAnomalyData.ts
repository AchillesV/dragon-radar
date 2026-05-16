import { useQuery } from '@tanstack/react-query';
import { fetchAnomalyCards, fetchAnomalyStocks } from '../api/client';
import type { AnomalyType } from '../types';

export function useAnomalyCards() {
  return useQuery({
    queryKey: ['anomaly', 'cards'],
    queryFn: fetchAnomalyCards,
    staleTime: 30000,
  });
}

export function useAnomalyStocks(type: AnomalyType) {
  return useQuery({
    queryKey: ['anomaly', 'stocks', type],
    queryFn: () => fetchAnomalyStocks(type),
    staleTime: 30000,
    enabled: !!type,
  });
}

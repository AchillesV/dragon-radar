import { useQuery } from '@tanstack/react-query';
import {
  fetchMarketOverview,
  fetchAmountHistory,
  fetchIndustrySectors,
  fetchConceptSectors,
  fetchFundFlow,
  fetchLianbanTiers,
} from '../api/client';

export function useMarketOverview() {
  return useQuery({
    queryKey: ['market', 'overview'],
    queryFn: fetchMarketOverview,
    refetchInterval: 30000,
  });
}

export function useAmountHistory() {
  return useQuery({
    queryKey: ['market', 'amount-history'],
    queryFn: fetchAmountHistory,
    staleTime: 60000,
  });
}

export function useIndustrySectors() {
  return useQuery({
    queryKey: ['market', 'industry-sectors'],
    queryFn: fetchIndustrySectors,
    staleTime: 30000,
  });
}

export function useConceptSectors() {
  return useQuery({
    queryKey: ['market', 'concept-sectors'],
    queryFn: fetchConceptSectors,
    staleTime: 30000,
  });
}

export function useFundFlow() {
  return useQuery({
    queryKey: ['market', 'fund-flow'],
    queryFn: fetchFundFlow,
    staleTime: 30000,
  });
}

export function useLianbanTiers() {
  return useQuery({
    queryKey: ['market', 'lianban'],
    queryFn: fetchLianbanTiers,
    staleTime: 30000,
  });
}

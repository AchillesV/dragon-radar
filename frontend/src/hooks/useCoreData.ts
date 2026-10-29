import { useQuery } from '@tanstack/react-query';
import { fetchCoreResult } from '../api/client';

export function useCoreResult() {
  return useQuery({
    queryKey: ['core', 'result'],
    queryFn: fetchCoreResult,
    staleTime: 60 * 1000,
  });
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchBoardPicks, fetchBoardDates, syncBoardPicks } from '../api/client';

// 「打板」每日选股
export function useBoardPicks(date?: string) {
  return useQuery({
    queryKey: ['board', 'picks', date ?? 'latest'],
    queryFn: () => fetchBoardPicks(date),
    staleTime: 5 * 60 * 1000,
  });
}

export function useBoardDates() {
  return useQuery({
    queryKey: ['board', 'dates'],
    queryFn: fetchBoardDates,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSyncBoardPicks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: syncBoardPicks,
    onSuccess: (picks) => {
      queryClient.setQueryData(['board', 'picks', 'latest'], picks);
      queryClient.invalidateQueries({ queryKey: ['board', 'dates'] });
    },
  });
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchBoardPicks, fetchBoardDates, fetchBoardPreselection, syncBoardPicks } from '../api/client';

// 「打板」默认视图（盘中为最终，其余为下一交易日预选）
export function useBoardPreselection() {
  return useQuery({
    queryKey: ['board', 'preselection'],
    queryFn: fetchBoardPreselection,
    staleTime: 60 * 1000,
  });
}

// 历史最终选股（按日期只读）
export function useBoardPicks(date?: string) {
  return useQuery({
    queryKey: ['board', 'picks', date ?? 'latest'],
    queryFn: () => fetchBoardPicks(date as string),
    enabled: !!date,
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
    onSuccess: (result) => {
      queryClient.setQueryData(['board', 'preselection'], result);
      queryClient.invalidateQueries({ queryKey: ['board', 'dates'] });
      queryClient.invalidateQueries({ queryKey: ['board', 'picks'] });
    },
  });
}

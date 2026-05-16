import { useQuery } from '@tanstack/react-query';
import { fetchScreeningStocks } from '../api/client';
import { useAppStore } from '../store';

export function useScreeningStocks() {
  const selectedFeatures = useAppStore((s) => s.selectedFeatures);

  return useQuery({
    queryKey: ['screening', 'stocks', selectedFeatures],
    queryFn: () => fetchScreeningStocks(selectedFeatures),
    staleTime: 30000,
    enabled: selectedFeatures.length > 0,
  });
}

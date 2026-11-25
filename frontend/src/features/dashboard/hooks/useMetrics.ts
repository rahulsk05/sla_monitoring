import { useQuery } from "@tanstack/react-query";

import { metricsService } from "../services/metrics.service";
import { METRICS_QUERY_KEYS } from "../constants/metrics.constants";

export function useMetrics() {
  return useQuery({
    queryKey: METRICS_QUERY_KEYS.DASHBOARD,
    queryFn: metricsService.getMetrics,
    refetchInterval: 60_000,
  });
}

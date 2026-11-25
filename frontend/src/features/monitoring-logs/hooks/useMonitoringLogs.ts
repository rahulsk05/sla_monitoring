import { useQuery } from "@tanstack/react-query";

import { monitoringLogsService } from "../services/monitoring-logs.service";
import type { GetMonitoringLogsParams } from "../api/monitoring-logs.api";
import { MONITORING_LOGS_QUERY_KEYS } from "../constants/monitoring-logs.contants";

export function useMonitoringLogs(params?: GetMonitoringLogsParams) {
  return useQuery({
    queryKey: MONITORING_LOGS_QUERY_KEYS.LIST(params),
    queryFn: () => monitoringLogsService.getMonitoringLogs(params),
  });
}
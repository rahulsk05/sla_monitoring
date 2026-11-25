import { logsApi } from "../../../lib/axios";
import type { LogsResponse } from "../types/monitoring-logs.types";

export interface GetMonitoringLogsParams {
  page?: number;
  date?: string;
  start_date?: string;
  end_date?: string;
}

export const getMonitoringLogs = async (
  params?: GetMonitoringLogsParams,
): Promise<LogsResponse> => {
  const response = await logsApi.get<LogsResponse>("/", {
    params,
  });

  return response.data;
};

import {
  getMonitoringLogs,
  type GetMonitoringLogsParams,
} from "../api/monitoring-logs.api";

export const monitoringLogsService = {
  getMonitoringLogs: (params?: GetMonitoringLogsParams) =>
    getMonitoringLogs(params),
};

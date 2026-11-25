export const MONITORING_LOGS_QUERY_KEYS = {
  ALL: ["monitoring-logs"] as const,
  LIST: (params?: {
    page?: number;
    date?: string;
    start_date?: string;
    end_date?: string;
  }) => [...MONITORING_LOGS_QUERY_KEYS.ALL, params] as const,
};

export interface LogRecord {
  id: number;
  record_hash: string;
  service_id: string;
  service_name: string;
  observed_at: string;
  status_code: number;
  latency_ms: string | null;
  agent: string;
  region: string;
  upload_id: string;
  created_at: string;
}

export interface LogsPagination {
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
}

export interface LogsResponse {
  success: boolean;
  data: {
    logs: LogRecord[];
    pagination: LogsPagination;
  };
}

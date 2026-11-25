export interface OverallMetricsData {
  id: number;
  total_checks: number;
  availability_eligible_checks: number;
  successful_checks: number;
  failed_checks: number;
  availability_percentage: string;
  services_below_sla: number;
  total_failure_events: number;
  longest_failure_duration_seconds: number;
  sla_threshold_percentage: string;
  calculated_at: string;
  updated_at: string;
}

export interface ServiceMetricsData {
  service_id: string;
  service_name: string;
  total_checks: number;
  availability_eligible_checks: number;
  successful_checks: number;
  failed_checks: number;
  availability_percentage: string;
  average_latency_ms: string;
  p95_latency_ms: string;
  latency_sample_count: number;
  failure_events: number;
  longest_failure_duration_seconds: number;
  meets_sla: boolean;
  calculated_at: string;
  updated_at: string;
}

export interface MetricsResponse {
  success: boolean;
  data: {
    overall: OverallMetricsData;
    services: ServiceMetricsData[];
  };
}

export const API_ENDPOINTS = {
  METRICS: import.meta.env.VITE_METRICS_API_URL,
  LOGS: import.meta.env.VITE_LOGS_API_URL,
  UPLOAD: import.meta.env.VITE_UPLOAD_API_URL,
} as const;

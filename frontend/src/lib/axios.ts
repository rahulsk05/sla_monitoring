import axios from "axios";

export const metricsApi = axios.create({
  baseURL: import.meta.env.VITE_METRICS_API_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

export const logsApi = axios.create({
  baseURL: import.meta.env.VITE_LOGS_API_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

export const uploadApi = axios.create({
  baseURL: import.meta.env.VITE_UPLOAD_API_URL,
  timeout: 60000,
  headers: {
    Accept: "application/json",
  },
});

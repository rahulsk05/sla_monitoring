
import { metricsApi } from "../../../lib/axios";
import type { MetricsResponse } from "../types/metrics.types";

export const metricsService = {
  async getMetrics(): Promise<MetricsResponse> {
    const response = await metricsApi.get<MetricsResponse>("");

    if (!response.data.success) {
      throw new Error("Unable to fetch dashboard metrics.");
    }

    return response.data;
  },
};

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { csvUploadService } from "../services/csv-upload.service";
import { METRICS_QUERY_KEYS } from "../../dashboard/constants/metrics.constants";
import { MONITORING_LOGS_QUERY_KEYS } from "../../monitoring-logs/constants/monitoring-logs.contants";

export function useCSVUpload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: csvUploadService.upload,

    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: METRICS_QUERY_KEYS.ALL,
        }),
        queryClient.invalidateQueries({
          queryKey: MONITORING_LOGS_QUERY_KEYS.ALL,
        }),
      ]);
    },
  });
}

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChartColumn,
  faXmark,
  faCheck,
} from "@fortawesome/free-solid-svg-icons";

import type { ServiceMetricsData } from "../types/metrics.types";
import { formatDuration } from "../utils/format-duration";

interface ServiceMetricsModalProps {
  services: ServiceMetricsData[];
  onClose: () => void;
}

export default function ServiceMetricsModal({
  services,
  onClose,
}: ServiceMetricsModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="service-metrics-title"
        className="flex max-h-[70vh] min-h-0 w-full max-w-350 flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-2xl"
      >
        {/* Modal Header */}
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-border px-6">
          <div className="flex items-center gap-3">
            <FontAwesomeIcon
              icon={faChartColumn}
              className="text-xl text-primary"
            />

            <h2
              id="service-metrics-title"
              className="text-lg font-semibold text-text-primary"
            >
              Service-wise Metrics
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close service metrics"
            className="flex size-9 items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-slate-100 hover:text-text-primary"
          >
            <FontAwesomeIcon icon={faXmark} className="text-xl" />
          </button>
        </div>

        {/* Table Container */}
        <div className="min-h-0 flex-1 overflow-y-auto overflow-x-auto p-4">
          {services.length === 0 ? (
            <div className="flex h-40 items-center justify-center text-sm text-text-secondary">
              No service metrics available.
            </div>
          ) : (
            <table className="w-full min-w-287.5 border-collapse text-sm">
              <thead className="sticky top-0 z-10 bg-surface-secondary">
                <tr className="text-text-primary">
                  <th className="px-4 py-3 text-center font-semibold">Service</th>

                  <th className="px-4 py-3 text-center font-semibold">
                    Total Health Checks
                  </th>

                  <th className="px-4 py-3 text-center font-semibold">
                    Availability
                  </th>

                  <th className="px-4 py-3 text-center font-semibold">
                    Average Latency (ms)
                  </th>

                  <th className="px-4 py-3 text-center font-semibold">
                    p95 Latency (ms)
                  </th>

                  <th className="px-4 py-3 text-center font-semibold">
                    Failed Checks
                  </th>

                  <th className="px-4 py-3 text-center font-semibold">
                    Failure Events
                  </th>

                  <th className="px-4 py-3 text-center font-semibold">
                    Longest Failure Duration
                  </th>

                  <th className="px-4 py-3 text-center font-semibold">
                    Met SLA
                  </th>
                </tr>
              </thead>

              <tbody>
                {services.map((service) => (
                  <tr
                    key={service.service_id}
                    className="border-b border-border transition-colors hover:bg-surface-secondary/70"
                  >
                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      {service.service_name}
                    </td>

                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      {service.total_checks.toLocaleString("en-IN")}
                    </td>

                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      <span
                        className={`inline-flex min-w-20 justify-center rounded-md px-3 py-1 font-semibold ${
                          service.meets_sla
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {service.availability_percentage}%
                      </span>
                    </td>

                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      {Number(service.average_latency_ms).toFixed(1)}
                    </td>

                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      {Number(service.p95_latency_ms).toFixed(1)}
                    </td>

                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      {service.failed_checks.toLocaleString("en-IN")}
                    </td>

                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      {service.failure_events.toLocaleString("en-IN")}
                    </td>

                    <td className="whitespace-nowrap px-4 py-3 text-center">
                      {formatDuration(service.longest_failure_duration_seconds)}
                    </td>

                    <td className="px-4 py-3 text-center">
                      <FontAwesomeIcon
                        icon={service.meets_sla ? faCheck : faXmark}
                        className={
                          service.meets_sla
                            ? "text-lg text-green-600"
                            : "text-lg text-red-600"
                        }
                        aria-label={
                          service.meets_sla ? "Met SLA" : "Did not meet SLA"
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

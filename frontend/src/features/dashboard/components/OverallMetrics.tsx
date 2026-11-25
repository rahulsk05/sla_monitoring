import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChartColumn,
  faChevronUp,
  faChevronDown,
  faTableCells,
} from "@fortawesome/free-solid-svg-icons";

import type { OverallMetricsData } from "../types/metrics.types";
import { formatDuration } from "../utils/format-duration";
import { OVERALL_METRIC_CONFIG } from "../../../constants/dashboard.constants";

interface OverallMetricsProps {
  data: OverallMetricsData;
  onServiceMetricsClick: () => void;
}

const METRIC_COLOR_CLASSES = {
  success: {
    icon: "bg-success/10 text-success",
    value: "text-success",
  },
  primary: {
    icon: "bg-primary/10 text-primary",
    value: "text-primary",
  },
  danger: {
    icon: "bg-danger/10 text-danger",
    value: "text-danger",
  },
  warning: {
    icon: "bg-warning/10 text-warning",
    value: "text-warning",
  },
  purple: {
    icon: "bg-purple-100 text-purple-700",
    value: "text-purple-700",
  },
  info: {
    icon: "bg-blue-100 text-blue-700",
    value: "text-blue-700",
  },
} as const;

export default function OverallMetrics({
  data,
  onServiceMetricsClick,
}: OverallMetricsProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const getMetricValue = (
    field: (typeof OVERALL_METRIC_CONFIG)[number]["field"],
  ): string => {
    switch (field) {
      case "longest_failure_duration_seconds":
        return formatDuration(data[field]);

      case "availability_percentage":
        return `${data[field]}%`;

      default:
        return data[field].toLocaleString("en-IN");
    }
  };

  return (
    <section
      className={`flex shrink-0 flex-col overflow-hidden rounded-lg border border-border bg-surface ${
        isExpanded ? "min-h-37.5 basis-[20%]" : "basis-auto"
      }`}
    >
      {/* Section Header */}
      <div className="flex h-11 shrink-0 items-center justify-between border-b border-border bg-surface-secondary px-4">
        <div className="flex items-center gap-2">
          <FontAwesomeIcon icon={faChartColumn} className="text-primary" />

          <h2 className="text-base font-semibold text-text-primary">
            Overall Metrics
          </h2>
        </div>

        <button
          type="button"
          aria-label={isExpanded ? "Collapse metrics" : "Expand metrics"}
          aria-expanded={isExpanded}
          onClick={() => setIsExpanded((previous) => !previous)}
          className="flex size-8 items-center justify-center rounded-md text-text-secondary transition-colors hover:bg-black/5"
        >
          <FontAwesomeIcon icon={isExpanded ? faChevronUp : faChevronDown} />
        </button>
      </div>

      {/* Metrics Content */}
      {isExpanded && (
        <div className="flex min-h-0 flex-1 items-stretch gap-3 overflow-hidden p-3">
          {/* Metric Cards */}
          <div className="grid min-w-0 flex-1 grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
            {OVERALL_METRIC_CONFIG.map((metric) => {
              const colors = METRIC_COLOR_CLASSES[metric.color];
              const value = getMetricValue(metric.field);

              return (
                <article
                  key={metric.id}
                  className="flex min-w-0 min-h-0 items-center gap-2.5 overflow-hidden rounded-lg border border-border px-2.5 py-2 sm:gap-3 sm:px-3"
                >
                  {/* Metric Icon */}
                  <div
                    className={`flex size-10 shrink-0 items-center justify-center rounded-lg sm:size-11 ${colors.icon}`}
                  >
                    <FontAwesomeIcon
                      icon={metric.icon}
                      className="text-lg sm:text-xl"
                    />
                  </div>

                  {/* Metric Details */}
                  <div className="flex min-w-0 flex-1 flex-col justify-center gap-1.5">
                    <span className="line-clamp-2 text-[13px] font-medium leading-tight text-text-secondary">
                      {metric.label}
                    </span>

                    <strong
                      className={`whitespace-nowrap text-xl font-bold leading-tight sm:text-[22px] ${colors.value}`}
                      title={value}
                    >
                      {value}
                    </strong>
                  </div>
                </article>
              );
            })}
          </div>

          {/* Service Metrics Action */}
          <div className="flex w-55 shrink-0 items-center justify-center border-l border-border pl-3">
            <button
              type="button"
              onClick={onServiceMetricsClick}
              className="flex h-12 w-full items-center justify-center gap-2 whitespace-nowrap rounded-md bg-primary px-3 text-sm font-semibold text-white transition-colors hover:bg-primary-hover"
            >
              <FontAwesomeIcon icon={faTableCells} className="shrink-0" />

              <span>Service-wise Metrics</span>
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

import {
  faCircleCheck,
  faHeartbeat,
  faCircleXmark,
  faTriangleExclamation,
  faClock,
  faLayerGroup,
} from "@fortawesome/free-solid-svg-icons";

export const OVERALL_METRIC_CONFIG = [
  {
    id: "availability",
    label: "Overall Availability",
    field: "availability_percentage",
    icon: faCircleCheck,
    color: "success",
    suffix: "%",
  },
  {
    id: "total-checks",
    label: "Total Health Checks",
    field: "total_checks",
    icon: faHeartbeat,
    color: "primary",
  },
  {
    id: "failed-checks",
    label: "Failed Checks",
    field: "failed_checks",
    icon: faCircleXmark,
    color: "danger",
  },
  {
    id: "failure-events",
    label: "Failure Events",
    field: "total_failure_events",
    icon: faTriangleExclamation,
    color: "warning",
  },
  {
    id: "longest-failure",
    label: "Longest Failure Duration",
    field: "longest_failure_duration_seconds",
    icon: faClock,
    color: "purple",
  },
  {
    id: "services-below-sla",
    label: "Services Below SLA",
    field: "services_below_sla",
    icon: faLayerGroup,
    color: "info",
  },
] as const;

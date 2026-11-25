import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faWaveSquare, faRotate } from "@fortawesome/free-solid-svg-icons";

interface DashboardHeaderProps {
  lastUpdated?: string;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export default function DashboardHeader({
  lastUpdated,
  onRefresh,
  isRefreshing = false,
}: DashboardHeaderProps) {
  return (
    <header className="flex h-13 min-h-13 shrink-0 items-center justify-between bg-primary px-3 text-white sm:px-5">
      <div className="flex items-center gap-2 sm:gap-3">
        <FontAwesomeIcon icon={faWaveSquare} className="text-xl sm:text-2xl" />

        <h1 className="text-sm font-semibold sm:text-base">
          SLA Monitoring Dashboard
        </h1>
      </div>

      <div className="flex items-center gap-2 text-xs sm:gap-3 sm:text-sm">
        <span>Last updated: {lastUpdated ?? "Not available"}</span>

        <button
          type="button"
          onClick={onRefresh}
          disabled={!onRefresh || isRefreshing}
          aria-label="Refresh dashboard metrics"
          title="Refresh metrics"
          className="flex size-8 items-center justify-center rounded-md transition-colors hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FontAwesomeIcon icon={faRotate} spin={isRefreshing} />
        </button>
      </div>
    </header>
  );
}

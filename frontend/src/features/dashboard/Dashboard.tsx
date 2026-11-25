import { useState } from "react";

import OverallMetrics from "./components/OverallMetrics";
import ServiceMetricsModal from "./components/ServiceMetricsModal";
import DashboardHeader from "./components/DashboardHeader";
import DashboardFooter from "./components/DashboardFooter";
import { useMetrics } from "./hooks/useMetrics";
import MonitoringLogs from "../monitoring-logs/components/MonitorLogs";

export default function Dashboard() {
  const [isServiceMetricsOpen, setIsServiceMetricsOpen] = useState(false);

  const { data, isLoading, isFetching, isError, refetch } = useMetrics();

  const overallMetrics = data?.data.overall;
  const serviceMetrics = data?.data.services ?? [];

  return (
    <div className="flex h-dvh w-full flex-col overflow-hidden bg-background">
      <DashboardHeader
        lastUpdated={overallMetrics?.updated_at}
        onRefresh={() => void refetch()}
        isRefreshing={isFetching}
      />

      <main className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden p-2">
        {isLoading && (
          <div
            role="status"
            className="flex min-h-37.5 shrink-0 items-center justify-center rounded-lg border border-border bg-surface text-sm text-text-secondary"
          >
            Loading dashboard metrics...
          </div>
        )}

        {isError && (
          <div
            role="alert"
            className="flex min-h-37.5 shrink-0 items-center justify-center gap-4 rounded-lg border border-border bg-surface p-4"
          >
            <span className="text-sm text-danger">
              Unable to load dashboard metrics.
            </span>

            <button
              type="button"
              onClick={() => void refetch()}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
            >
              Retry
            </button>
          </div>
        )}

        {overallMetrics && (
          <OverallMetrics
            data={overallMetrics}
            onServiceMetricsClick={() => setIsServiceMetricsOpen(true)}
          />
        )}

        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-border bg-surface">
          <MonitoringLogs />
        </section>
      </main>

      <DashboardFooter />

      {isServiceMetricsOpen && (
        <ServiceMetricsModal
          services={serviceMetrics}
          onClose={() => setIsServiceMetricsOpen(false)}
        />
      )}
    </div>
  );
}

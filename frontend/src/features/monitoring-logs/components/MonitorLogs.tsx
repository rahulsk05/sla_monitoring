import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCloudArrowUp } from "@fortawesome/free-solid-svg-icons";

import { useMonitoringLogs } from "../hooks/useMonitoringLogs";
import CSVUploadModal from "../../csv-upload/components/CSVUploadModal";

type DateFilterMode = "single" | "range";

const TABLE_HEADERS = [
  "Timestamp",
  "Service ID",
  "Service Name",
  "Status Code",
  "Latency (ms)",
  "Agent",
  "Region",
] as const;

function formatCellValue(value: string | number | null | undefined): string {
  if (
    value === null ||
    value === undefined ||
    (typeof value === "string" && value.trim() === "")
  ) {
    return "—";
  }

  return String(value);
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value || value.trim() === "") {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

export default function MonitoringLogs() {
  const [page, setPage] = useState(1);
  const [filterMode, setFilterMode] = useState<DateFilterMode>("single");

  const [selectedDate, setSelectedDate] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const [appliedFilters, setAppliedFilters] = useState<{
    date?: string;
    start_date?: string;
    end_date?: string;
  }>({});

  const { data, isLoading, isFetching, isError, refetch } = useMonitoringLogs({
    page,
    ...appliedFilters,
  });

  const logs = data?.data.logs ?? [];
  const pagination = data?.data.pagination;

  const handleApplyFilters = () => {
    if (filterMode === "single") {
      setAppliedFilters(selectedDate ? { date: selectedDate } : {});
    } else {
      setAppliedFilters({
        ...(startDate && { start_date: startDate }),
        ...(endDate && { end_date: endDate }),
      });
    }

    setPage(1);
  };

  const handleClearFilters = () => {
    setSelectedDate("");
    setStartDate("");
    setEndDate("");
    setAppliedFilters({});
    setPage(1);
  };

  const handleFilterModeChange = (mode: DateFilterMode) => {
    setFilterMode(mode);
    setSelectedDate("");
    setStartDate("");
    setEndDate("");
  };

  const hasActiveFilters = Object.keys(appliedFilters).length > 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border p-3">
        <div>
          <h2 className="text-base font-semibold text-text-primary">
            Health Check Logs
          </h2>

          <p className="mt-1 text-xs text-text-secondary">
            Monitor health check activity across services
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label
            htmlFor="log-date-filter"
            className="text-xs font-medium text-text-secondary"
          >
            Filter by
          </label>

          <select
            id="log-date-filter"
            value={filterMode}
            onChange={(event) =>
              handleFilterModeChange(event.target.value as DateFilterMode)
            }
            className="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary"
          >
            <option value="single">Single Date</option>
            <option value="range">Date Range</option>
          </select>

          {filterMode === "single" ? (
            <input
              type="date"
              aria-label="Select date"
              value={selectedDate}
              onChange={(event) => setSelectedDate(event.target.value)}
              className="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary"
            />
          ) : (
            <>
              <input
                type="date"
                aria-label="Start date"
                value={startDate}
                max={endDate || undefined}
                onChange={(event) => setStartDate(event.target.value)}
                className="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary"
              />

              <span className="text-xs text-text-secondary">to</span>

              <input
                type="date"
                aria-label="End date"
                value={endDate}
                min={startDate || undefined}
                onChange={(event) => setEndDate(event.target.value)}
                className="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary"
              />
            </>
          )}

          <button
            type="button"
            onClick={handleApplyFilters}
            disabled={
              filterMode === "single" ? !selectedDate : !startDate || !endDate
            }
            className="h-9 rounded-md bg-primary px-4 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            Apply
          </button>

          <button
            type="button"
            onClick={handleClearFilters}
            disabled={
              !hasActiveFilters && !selectedDate && !startDate && !endDate
            }
            className="h-9 rounded-md border border-border bg-surface px-3 text-sm font-medium text-text-secondary transition-colors hover:bg-surface-secondary disabled:cursor-not-allowed disabled:opacity-50"
          >
            Clear
          </button>

          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
          >
            <FontAwesomeIcon icon={faCloudArrowUp} />
            Upload CSV
          </button>
        </div>
      </div>

      {/* Results information */}
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border px-3 py-2">
        <span className="text-xs text-text-secondary">
          {pagination
            ? `${pagination.total_records} records found`
            : "Health check records"}
        </span>

        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="text-xs font-medium text-primary transition-colors hover:text-primary-hover disabled:opacity-50"
        >
          {isFetching ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Table content */}
      <div className="min-h-0 flex-1 overflow-auto">
        {isLoading ? (
          <div
            role="status"
            className="flex h-full min-h-40 items-center justify-center text-sm text-text-secondary"
          >
            Loading health check logs...
          </div>
        ) : isError ? (
          <div
            role="alert"
            className="flex h-full min-h-40 flex-col items-center justify-center gap-3"
          >
            <p className="text-sm text-danger">
              Unable to load health check logs.
            </p>

            <button
              type="button"
              onClick={() => void refetch()}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
            >
              Retry
            </button>
          </div>
        ) : logs.length === 0 ? (
          <div className="flex h-full min-h-40 items-center justify-center text-sm text-text-secondary">
            No health check logs found.
          </div>
        ) : (
          <table className="w-full min-w-237.5 border-collapse text-left text-sm">
            <thead className="sticky top-0 z-10 bg-surface-secondary">
              <tr>
                {TABLE_HEADERS.map((header) => (
                  <th
                    key={header}
                    scope="col"
                    className="whitespace-nowrap border-b border-border px-4 py-3 text-xs font-semibold text-text-secondary"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-border">
              {logs.map((log) => (
                <tr
                  key={log.id}
                  className="transition-colors hover:bg-surface-secondary/60"
                >
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-text-primary">
                    {formatTimestamp(log.observed_at)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 text-xs text-text-primary">
                    {formatCellValue(log.service_id)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 text-xs font-medium text-text-primary">
                    {formatCellValue(log.service_name)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3">
                    <span
                      className={`inline-flex rounded-md px-2 py-1 text-xs font-semibold ${
                        log.status_code >= 200 && log.status_code < 300
                          ? "bg-success/10 text-success"
                          : "bg-danger/10 text-danger"
                      }`}
                    >
                      {formatCellValue(log.status_code)}
                    </span>
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 text-xs text-text-primary">
                    {formatCellValue(log.latency_ms)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 text-xs text-text-primary">
                    {formatCellValue(log.agent)}
                  </td>

                  <td className="whitespace-nowrap px-4 py-3 text-xs text-text-primary">
                    {formatCellValue(log.region)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {pagination && pagination.total_pages > 0 && (
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-border bg-surface px-3 py-2">
          <span className="text-xs text-text-secondary">
            Page {pagination.page} of {pagination.total_pages}
            {" · "}
            {pagination.total_records} records
          </span>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPage((current) => current - 1)}
              disabled={pagination.page <= 1 || isFetching}
              className="h-8 rounded-md border border-border px-3 text-xs font-medium text-text-primary transition-colors hover:bg-surface-secondary disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>

            <button
              type="button"
              onClick={() => setPage((current) => current + 1)}
              disabled={pagination.page >= pagination.total_pages || isFetching}
              className="h-8 rounded-md border border-border px-3 text-xs font-medium text-text-primary transition-colors hover:bg-surface-secondary disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* CSV Upload Modal */}
      {isUploadModalOpen && (
        <CSVUploadModal onClose={() => setIsUploadModalOpen(false)} />
      )}
    </div>
  );
}

import { APP_CONFIG } from "../../../constants/app.contants";

export default function DashboardFooter() {
  return (
    <footer className="flex h-8 min-h-8 shrink-0 items-center justify-between border-t border-border bg-surface-secondary px-3 text-xs text-text-secondary sm:px-5">
      <span>{APP_CONFIG.NAME}</span>
      <span>Version {APP_CONFIG.VERSION}</span>
    </footer>
  );
}

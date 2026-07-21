import { AlertTriangle, Ban, RotateCw, SearchX, ServerCrash } from "lucide-react";
import { ApiError } from "@/lib/utils/errors";
import { Button } from "./Button";

/**
 * Renders a distinct state per ApiError.kind for a primary page-level
 * query. 503 ("unavailable") and 403 ("forbidden") must read differently
 * at a glance — one means the backend is down, the other means the user
 * isn't allowed to see this — so each gets its own icon and tone, and only
 * the retryable kinds show a "Retry" button.
 */
export function QueryErrorState({
  error,
  onRetry,
  resourceLabel = "this page",
}: {
  error: unknown;
  onRetry?: () => void;
  resourceLabel?: string;
}) {
  const kind = error instanceof ApiError ? error.kind : "unknown";

  if (kind === "unavailable") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-accent-warning/30 bg-accent-warning/10 py-16 text-center">
        <ServerCrash size={28} strokeWidth={1.5} className="text-accent-warning-ink" aria-hidden />
        <div className="flex flex-col gap-1">
          <p className="font-display text-base font-semibold text-text-primary">
            Temporarily unavailable
          </p>
          <p className="max-w-sm text-sm text-text-muted">
            This data is temporarily unavailable — the service may be restarting. Try again
            shortly.
          </p>
        </div>
        {onRetry && (
          <Button variant="secondary" size="sm" onClick={onRetry} className="mt-2">
            <RotateCw size={14} strokeWidth={1.75} />
            Retry
          </Button>
        )}
      </div>
    );
  }

  if (kind === "forbidden") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border py-16 text-center">
        <Ban size={28} strokeWidth={1.5} className="text-text-muted" aria-hidden />
        <div className="flex flex-col gap-1">
          <p className="font-display text-base font-semibold text-text-primary">
            You don&apos;t have access
          </p>
          <p className="max-w-sm text-sm text-text-muted">
            You don&apos;t have access to {resourceLabel}.
          </p>
        </div>
      </div>
    );
  }

  if (kind === "not_found") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border py-16 text-center">
        <SearchX size={28} strokeWidth={1.5} className="text-text-muted" aria-hidden />
        <div className="flex flex-col gap-1">
          <p className="font-display text-base font-semibold text-text-primary">Not found</p>
          <p className="max-w-sm text-sm text-text-muted">
            {`${resourceLabel[0]?.toUpperCase() ?? ""}${resourceLabel.slice(1)} doesn't exist or was removed.`}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-accent-critical/30 bg-accent-critical/10 py-16 text-center">
      <AlertTriangle size={28} strokeWidth={1.5} className="text-accent-critical-ink" aria-hidden />
      <div className="flex flex-col gap-1">
        <p className="font-display text-base font-semibold text-text-primary">
          Something went wrong
        </p>
        <p className="max-w-sm text-sm text-text-muted">Something went wrong loading this page.</p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} className="mt-2">
          <RotateCw size={14} strokeWidth={1.75} />
          Retry
        </Button>
      )}
    </div>
  );
}

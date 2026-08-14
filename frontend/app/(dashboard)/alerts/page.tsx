"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Check, ShieldCheck } from "lucide-react";
import { acknowledgeAlert, listAlerts, resolveAlert } from "@/lib/api/notifications";
import { qk } from "@/lib/query/keys";
import { ApiError } from "@/lib/api-client";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/FormField";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";
import { useToast } from "@/components/ui/Toast";
import { AssetSelector, type AssetSelectorValue } from "@/components/shared/AssetSelector";
import { formatTimestamp } from "@/lib/utils/format";
import type { AlertOut } from "@/lib/api-types";

const STATUS_OPTIONS = ["", "open", "acknowledged", "resolved"] as const;
const STATUS_LABELS: Record<string, string> = {
  "": "All statuses",
  open: "Open",
  acknowledged: "Acknowledged",
  resolved: "Resolved",
};

function severityTone(severity: string): "warning" | "critical" {
  return severity === "critical" ? "critical" : "warning";
}

function statusTone(status: string): "neutral" | "primary" | "warning" {
  if (status === "resolved") return "primary";
  if (status === "acknowledged") return "neutral";
  return "warning";
}

function AlertRow({ assetId, alert }: { assetId: string; alert: AlertOut }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["alerts", assetId] });

  const acknowledge = useMutation({
    mutationFn: () => acknowledgeAlert(assetId, alert.id),
    onSuccess: () => {
      invalidate();
      showToast("Alert acknowledged");
    },
    onError: (err) => {
      showToast(err instanceof ApiError ? err.message : "Couldn't acknowledge alert.", "error");
    },
  });

  const resolve = useMutation({
    mutationFn: () => resolveAlert(assetId, alert.id),
    onSuccess: () => {
      invalidate();
      showToast("Alert resolved");
    },
    onError: (err) => {
      showToast(err instanceof ApiError ? err.message : "Couldn't resolve alert.", "error");
    },
  });

  return (
    <div className="flex flex-col gap-2 border-b border-border py-3 last:border-b-0 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex flex-1 flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={severityTone(alert.severity)}>{alert.severity}</Badge>
          <Badge tone={statusTone(alert.status)}>{alert.status}</Badge>
          <span className="font-mono text-xs uppercase tracking-wide text-text-subtle">
            {alert.source}
          </span>
        </div>
        <p className="text-sm text-text-primary">{alert.message}</p>
        <p className="font-mono-num text-xs text-text-muted">{formatTimestamp(alert.created_at)}</p>
      </div>
      {alert.status !== "resolved" && (
        <div className="flex shrink-0 items-center gap-2">
          {alert.status === "open" && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => acknowledge.mutate()}
              disabled={acknowledge.isPending}
            >
              <Check size={14} strokeWidth={1.75} />
              {acknowledge.isPending ? "Acknowledging…" : "Acknowledge"}
            </Button>
          )}
          <Button size="sm" onClick={() => resolve.mutate()} disabled={resolve.isPending}>
            <ShieldCheck size={14} strokeWidth={1.75} />
            {resolve.isPending ? "Resolving…" : "Resolve"}
          </Button>
        </div>
      )}
    </div>
  );
}

export default function AlertsPage() {
  const [selection, setSelection] = useState<AssetSelectorValue>({
    facilityId: null,
    assetId: null,
  });
  const [status, setStatus] = useState<string>("");

  const alertsQuery = useQuery({
    queryKey: qk.alerts(selection.assetId ?? "", status || undefined),
    queryFn: () => listAlerts(selection.assetId as string, { status: status || undefined }),
    enabled: !!selection.assetId,
  });

  return (
    <div className="flex flex-col gap-8">
      <header className="border-b-2 border-text-primary pb-4">
        <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
          #03 — ALERTS
        </p>
        <h1 className="font-display text-3xl font-bold leading-none text-text-primary sm:text-4xl">
          Alerts
        </h1>
      </header>

      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:gap-4">
          <div className="flex-[2]">
            <AssetSelector value={selection} onChange={setSelection} />
          </div>
          <div className="flex-1">
            <Select
              aria-label="Filter by status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              disabled={!selection.assetId}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {STATUS_LABELS[opt]}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </Card>

      {!selection.assetId && (
        <EmptyState
          icon={Bell}
          title="Select an asset"
          description="Choose a facility and asset above to view its alerts."
        />
      )}

      {selection.assetId && alertsQuery.isError && (
        <QueryErrorState
          error={alertsQuery.error}
          onRetry={() => alertsQuery.refetch()}
          resourceLabel="this asset's alerts"
        />
      )}

      {selection.assetId && !alertsQuery.isError && alertsQuery.isLoading && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      )}

      {selection.assetId &&
        !alertsQuery.isError &&
        !alertsQuery.isLoading &&
        alertsQuery.data?.length === 0 && (
          <EmptyState
            icon={Bell}
            title="No alerts"
            description="Nothing to show for this asset and filter."
          />
        )}

      {selection.assetId && !!alertsQuery.data?.length && (
        <Card>
          {alertsQuery.data.map((alert) => (
            <AlertRow key={alert.id} assetId={selection.assetId as string} alert={alert} />
          ))}
        </Card>
      )}
    </div>
  );
}

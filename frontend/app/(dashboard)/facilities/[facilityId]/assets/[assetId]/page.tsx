"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Cpu } from "lucide-react";
import { getAsset, listAssetTypes } from "@/lib/api/assets";
import { listTelemetry } from "@/lib/api/telemetry";
import { qk } from "@/lib/query/keys";
import { TELEMETRY_POLL_INTERVAL_MS } from "@/lib/reliability/constants";
import { applySimulatedReliability, deriveReliability } from "@/lib/reliability/deriveReliability";
import { useUnits } from "@/lib/units/UnitsProvider";
import { Card } from "@/components/ui/Card";
import { ReliabilityIndicator } from "@/components/ui/ReliabilityIndicator";
import { MonoValue } from "@/components/ui/MonoValue";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";
import { MetricMappingPanel } from "@/components/facility-admin/MetricMappingPanel";
import { MetricVisualization } from "@/components/metrics/MetricVisualization";
import { formatTimestamp } from "@/lib/utils/format";

export default function AssetDetailPage() {
  const { assetId } = useParams<{ facilityId: string; assetId: string }>();
  const searchParams = useSearchParams();
  const { formatValue } = useUnits();

  const assetQuery = useQuery({ queryKey: qk.asset(assetId), queryFn: () => getAsset(assetId) });
  const assetTypesQuery = useQuery({ queryKey: qk.assetTypes(), queryFn: listAssetTypes });
  const telemetryQuery = useQuery({
    queryKey: qk.telemetry(assetId),
    queryFn: () => listTelemetry(assetId),
    refetchInterval: TELEMETRY_POLL_INTERVAL_MS,
  });

  const assetType = assetTypesQuery.data?.find((t) => t.id === assetQuery.data?.asset_type_id);
  const readings = telemetryQuery.data ?? [];
  const lastRecordedAt = readings.reduce<string | null>(
    (latest, r) => (!latest || r.recorded_at > latest ? r.recorded_at : latest),
    null,
  );
  const reliability = applySimulatedReliability(deriveReliability(lastRecordedAt), searchParams);

  if (assetQuery.isError) {
    return (
      <QueryErrorState
        error={assetQuery.error}
        onRetry={() => assetQuery.refetch()}
        resourceLabel="this asset"
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu size={18} strokeWidth={1.75} className="text-text-muted" />
          <h1 className="font-display text-xl font-semibold text-text-primary">
            {assetQuery.data?.name ?? <Skeleton className="h-6 w-32" />}
          </h1>
        </div>
        {assetQuery.data && (
          <ReliabilityIndicator state={reliability} lastRecordedAt={lastRecordedAt} />
        )}
      </div>

      {telemetryQuery.isError && (
        <Card>
          <QueryErrorState
            error={telemetryQuery.error}
            onRetry={() => telemetryQuery.refetch()}
            resourceLabel="this asset's telemetry"
          />
        </Card>
      )}

      {!telemetryQuery.isError && telemetryQuery.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      )}

      {!telemetryQuery.isError &&
        !telemetryQuery.isLoading &&
        (assetType?.metric_definitions.length ?? 0) === 0 && (
          <p className="text-sm text-text-muted">No metrics defined for this asset type yet.</p>
        )}

      {!telemetryQuery.isError && !!assetType?.metric_definitions.length && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {assetType.metric_definitions.map((metric) => (
            <MetricVisualization
              key={metric.id}
              metric={metric}
              readings={readings.filter((r) => r.metric_definition_id === metric.id)}
            />
          ))}
        </div>
      )}

      <details className="group rounded-xl border border-border bg-surface p-4">
        <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-medium text-text-primary">
          Recent readings (raw)
          <ChevronDown
            size={16}
            strokeWidth={1.75}
            className="text-text-muted transition-transform group-open:rotate-180"
          />
        </summary>

        <div className="mt-4">
          {!telemetryQuery.isError && !telemetryQuery.isLoading && readings.length === 0 && (
            <p className="text-sm text-text-muted">No telemetry received for this asset yet.</p>
          )}

          {!telemetryQuery.isError && readings.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-text-muted">
                    <th className="py-2 pr-4 font-medium">Metric</th>
                    <th className="py-2 pr-4 font-medium">Value</th>
                    <th className="py-2 font-medium">Recorded</th>
                  </tr>
                </thead>
                <tbody>
                  {readings.slice(0, 25).map((reading) => {
                    const metric = assetType?.metric_definitions.find(
                      (m) => m.id === reading.metric_definition_id,
                    );
                    return (
                      <tr key={reading.id} className="border-b border-border last:border-b-0">
                        <td className="py-2 pr-4 text-text-primary">
                          {metric?.display_name ?? reading.external_key}
                        </td>
                        <td className="py-2 pr-4">
                          <MonoValue className="text-text-primary">
                            {formatValue(reading.value, metric?.unit)}
                          </MonoValue>
                        </td>
                        <td className="py-2 font-mono-num text-xs text-text-muted">
                          {formatTimestamp(reading.recorded_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </details>

      <Card>
        <MetricMappingPanel assetId={assetId} metrics={assetType?.metric_definitions ?? []} />
      </Card>
    </div>
  );
}

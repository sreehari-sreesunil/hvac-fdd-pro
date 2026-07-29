"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Cpu } from "lucide-react";
import { listTelemetry } from "@/lib/api/telemetry";
import { qk } from "@/lib/query/keys";
import { TELEMETRY_POLL_INTERVAL_MS } from "@/lib/reliability/constants";
import { applySimulatedReliability, deriveReliability } from "@/lib/reliability/deriveReliability";
import { Card, CardHeader } from "@/components/ui/Card";
import { ReliabilityIndicator } from "@/components/ui/ReliabilityIndicator";
import { Skeleton } from "@/components/ui/Skeleton";
import { MetricRow } from "./MetricRow";
import { KpiTile } from "@/components/metrics/KpiTile";
import type { AssetOut, AssetTypeOut, TelemetryReadingOut } from "@/lib/api-types";

const MAX_KPI_TILES = 3;

export function AssetCard({
  asset,
  assetType,
  facilityId,
}: {
  asset: AssetOut;
  assetType: AssetTypeOut | undefined;
  facilityId: string;
}) {
  const searchParams = useSearchParams();
  const telemetryQuery = useQuery({
    queryKey: qk.telemetry(asset.id),
    queryFn: () => listTelemetry(asset.id),
    refetchInterval: TELEMETRY_POLL_INTERVAL_MS,
  });

  const readings = telemetryQuery.data ?? [];
  const readingsByMetric = new Map<string, TelemetryReadingOut[]>();
  const latestByMetric = new Map<string, number>();
  let lastRecordedAt: string | null = null;
  for (const reading of readings) {
    if (!reading.metric_definition_id) continue;
    const existing = latestByMetric.get(reading.metric_definition_id);
    if (existing === undefined) latestByMetric.set(reading.metric_definition_id, reading.value);
    const bucket = readingsByMetric.get(reading.metric_definition_id);
    if (bucket) bucket.push(reading);
    else readingsByMetric.set(reading.metric_definition_id, [reading]);
    if (!lastRecordedAt || reading.recorded_at > lastRecordedAt) {
      lastRecordedAt = reading.recorded_at;
    }
  }

  const actualReliability = deriveReliability(lastRecordedAt);
  const reliability = applySimulatedReliability(actualReliability, searchParams);

  const kpiMetrics = (assetType?.metric_definitions ?? []).filter((m) => m.chart_type === "kpi");
  const otherMetrics = (assetType?.metric_definitions ?? []).filter((m) => m.chart_type !== "kpi");

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Cpu size={16} strokeWidth={1.75} className="text-text-muted" aria-hidden />
          <Link
            href={`/facilities/${facilityId}/assets/${asset.id}`}
            className="font-display text-base font-semibold text-text-primary hover:text-accent-primary-ink"
          >
            {asset.name}
          </Link>
        </div>
        <ReliabilityIndicator state={reliability} lastRecordedAt={lastRecordedAt} />
      </CardHeader>

      {telemetryQuery.isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-5 w-full" />
        </div>
      ) : assetType && assetType.metric_definitions.length > 0 ? (
        <div className="flex flex-col gap-3">
          {kpiMetrics.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {kpiMetrics.slice(0, MAX_KPI_TILES).map((metric) => (
                <KpiTile
                  key={metric.id}
                  metric={metric}
                  readings={readingsByMetric.get(metric.id) ?? []}
                />
              ))}
            </div>
          )}
          {otherMetrics.length > 0 && (
            <div>
              {otherMetrics.map((metric) => (
                <MetricRow
                  key={metric.id}
                  metric={metric}
                  value={latestByMetric.get(metric.id) ?? null}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-text-muted">No metrics defined for this asset type yet.</p>
      )}
    </Card>
  );
}

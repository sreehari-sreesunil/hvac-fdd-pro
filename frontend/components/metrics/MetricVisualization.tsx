"use client";

import { deriveReliability } from "@/lib/reliability/deriveReliability";
import { ReliabilityIndicator } from "@/components/ui/ReliabilityIndicator";
import { LineChartView } from "./LineChartView";
import { GaugeView } from "./GaugeView";
import { KpiView } from "./KpiView";
import type { MetricDefinitionOut, TelemetryReadingOut } from "@/lib/api-types";

/**
 * Dispatches to the chart-type-specific view for one metric, and renders
 * the shared reliability badge (live/stale/disconnected) above it — each
 * metric on an asset can have its own data freshness, so this is computed
 * per metric rather than once per asset.
 */
export function MetricVisualization({
  metric,
  readings,
}: {
  metric: MetricDefinitionOut;
  readings: TelemetryReadingOut[];
}) {
  const lastRecordedAt = readings.reduce<string | null>(
    (latest, r) => (!latest || r.recorded_at > latest ? r.recorded_at : latest),
    null,
  );
  const reliability = deriveReliability(lastRecordedAt);

  return (
    <div className="flex flex-col gap-3 rounded-surface bg-neo-base p-4 shadow-neo-resting">
      <div className="flex items-center justify-between gap-2">
        <span className="font-display text-sm font-semibold text-text-primary">
          {metric.display_name}
        </span>
        <ReliabilityIndicator state={reliability} lastRecordedAt={lastRecordedAt} />
      </div>

      {metric.chart_type === "gauge" ? (
        <GaugeView metric={metric} readings={readings} />
      ) : metric.chart_type === "kpi" ? (
        <KpiView metric={metric} readings={readings} />
      ) : (
        <LineChartView metric={metric} readings={readings} />
      )}
    </div>
  );
}

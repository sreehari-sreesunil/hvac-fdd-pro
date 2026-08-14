"use client";

import { useUnits } from "@/lib/units/UnitsProvider";
import { convertForDisplay } from "@/lib/units/convert";
import { MonoValue } from "@/components/ui/MonoValue";
import type { MetricDefinitionOut, TelemetryReadingOut } from "@/lib/api-types";

/** Compact numeral-only tile for dashboard overview cards — no trend, no
 *  chart, just the latest value. Full KpiView (with trend) is reserved for
 *  the asset detail page. */
export function KpiTile({
  metric,
  readings,
}: {
  metric: MetricDefinitionOut;
  readings: TelemetryReadingOut[];
}) {
  const { system } = useUnits();
  const latest = readings.reduce<TelemetryReadingOut | null>(
    (acc, r) => (!acc || r.recorded_at > acc.recorded_at ? r : acc),
    null,
  );

  if (!latest) return null;

  const { value, unit } = convertForDisplay(latest.value, metric.unit, system);

  return (
    <div className="flex min-w-0 flex-col gap-0.5 rounded-surface bg-neo-base px-2.5 py-1.5 shadow-neo-resting">
      <span className="truncate font-mono text-[11px] uppercase tracking-wide text-text-muted">
        {metric.display_name}
      </span>
      <MonoValue className="text-sm font-medium text-text-primary">
        {value.toFixed(1)}
        {unit}
      </MonoValue>
    </div>
  );
}

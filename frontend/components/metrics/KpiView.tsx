"use client";

import { ArrowDown, ArrowUp } from "lucide-react";
import { useUnits } from "@/lib/units/UnitsProvider";
import { convertForDisplay } from "@/lib/units/convert";
import { MonoValue } from "@/components/ui/MonoValue";
import type { MetricDefinitionOut, TelemetryReadingOut } from "@/lib/api-types";

export function KpiView({
  metric,
  readings,
  note,
}: {
  metric: MetricDefinitionOut;
  readings: TelemetryReadingOut[];
  /** Used by GaugeView's no-range fallback to explain why it looks like this. */
  note?: string;
}) {
  const { system } = useUnits();
  const sorted = [...readings].sort((a, b) => a.recorded_at.localeCompare(b.recorded_at));
  const latest = sorted[sorted.length - 1];
  const previous = sorted[sorted.length - 2];

  if (!latest) {
    return <p className="text-sm text-text-muted">No readings yet.</p>;
  }

  const { value: latestValue, unit } = convertForDisplay(latest.value, metric.unit, system);

  let trend: { direction: "up" | "down"; delta: number } | null = null;
  if (previous) {
    const { value: previousValue } = convertForDisplay(previous.value, metric.unit, system);
    const delta = latestValue - previousValue;
    // Omit the indicator when there's no real change to report rather than
    // showing a meaningless flat arrow.
    if (Math.abs(delta) > 0.001) {
      trend = { direction: delta > 0 ? "up" : "down", delta: Math.abs(delta) };
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline gap-1">
        <MonoValue as="div" className="text-3xl font-semibold text-text-primary">
          {latestValue.toFixed(1)}
        </MonoValue>
        <span className="font-mono-num text-lg text-text-muted">{unit}</span>
      </div>
      {trend && (
        <p className="flex items-center gap-1 text-xs text-text-muted">
          {trend.direction === "up" ? (
            <ArrowUp size={12} strokeWidth={2} aria-hidden />
          ) : (
            <ArrowDown size={12} strokeWidth={2} aria-hidden />
          )}
          <span className="font-mono-num">
            {trend.delta.toFixed(1)}
            {unit}
          </span>
          since last reading
        </p>
      )}
      {note && <p className="text-xs text-text-muted">{note}</p>}
    </div>
  );
}

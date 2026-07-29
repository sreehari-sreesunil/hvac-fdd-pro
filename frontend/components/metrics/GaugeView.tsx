"use client";

import { useUnits } from "@/lib/units/UnitsProvider";
import { convertForDisplay } from "@/lib/units/convert";
import { KpiView } from "./KpiView";
import type { MetricDefinitionOut, TelemetryReadingOut } from "@/lib/api-types";

const CX = 100;
const CY = 100;
const R = 78;
const STROKE = 14;

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const angleRad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(angleRad), y: cy - r * Math.sin(angleRad) };
}

/** Traces the arc clockwise (as drawn on screen) from startAngle to endAngle,
 *  where 180deg is the leftmost point and 0deg is the rightmost — i.e. the
 *  standard semi-circular gauge sitting on its flat bottom edge. */
function describeArc(startAngle: number, endAngle: number) {
  const start = polarToCartesian(CX, CY, R, startAngle);
  const end = polarToCartesian(CX, CY, R, endAngle);
  const largeArcFlag = Math.abs(startAngle - endAngle) > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${R} ${R} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`;
}

/**
 * Semi-circular arc gauge. Shows position within [min_value, max_value]
 * only — no severity-zone coloring, since there's no alert-thresholds
 * concept in the data model yet (a future roadmap item). Falls back to the
 * KPI large-numeral treatment when no range is configured, rather than
 * guessing bounds from whatever readings happen to be visible.
 */
export function GaugeView({
  metric,
  readings,
}: {
  metric: MetricDefinitionOut;
  readings: TelemetryReadingOut[];
}) {
  const { system } = useUnits();

  if (metric.min_value == null || metric.max_value == null) {
    return <KpiView metric={metric} readings={readings} note="No range configured for this metric yet." />;
  }

  const sorted = [...readings].sort((a, b) => a.recorded_at.localeCompare(b.recorded_at));
  const latest = sorted[sorted.length - 1];

  if (!latest) {
    return <p className="text-sm text-text-muted">No readings yet.</p>;
  }

  const { value: boundA } = convertForDisplay(metric.min_value, metric.unit, system);
  const { value: boundB } = convertForDisplay(metric.max_value, metric.unit, system);
  const { value: current, unit } = convertForDisplay(latest.value, metric.unit, system);

  const lo = Math.min(boundA, boundB);
  const hi = Math.max(boundA, boundB);
  const fraction = hi === lo ? 0 : Math.min(1, Math.max(0, (current - lo) / (hi - lo)));
  const endAngle = 180 - fraction * 180;

  const trackPath = describeArc(180, 0);
  const fillPath = fraction > 0 ? describeArc(180, endAngle) : null;

  return (
    <div className="flex flex-col items-center">
      <svg
        viewBox="0 0 200 118"
        className="w-full max-w-[220px]"
        role="img"
        aria-label={`${metric.display_name}, ${current.toFixed(1)} of ${lo.toFixed(0)} to ${hi.toFixed(0)} ${unit}`}
      >
        <path d={trackPath} fill="none" stroke="var(--border)" strokeWidth={STROKE} strokeLinecap="round" />
        {fillPath && (
          <path
            d={fillPath}
            fill="none"
            stroke="var(--accent-primary)"
            strokeWidth={STROKE}
            strokeLinecap="round"
          />
        )}
        <text
          x={CX}
          y={CY - 16}
          textAnchor="middle"
          className="font-mono-num"
          fontSize="22"
          fontWeight="600"
          fill="var(--text-primary)"
        >
          {current.toFixed(1)}
          <tspan fontSize="12" fill="var(--text-muted)">
            {" "}
            {unit}
          </tspan>
        </text>
        <text
          x={polarToCartesian(CX, CY, R + 18, 180).x}
          y={CY + 6}
          textAnchor="start"
          fontSize="11"
          fill="var(--text-muted)"
          className="font-mono-num"
        >
          {lo.toFixed(0)}
        </text>
        <text
          x={polarToCartesian(CX, CY, R + 18, 0).x}
          y={CY + 6}
          textAnchor="end"
          fontSize="11"
          fill="var(--text-muted)"
          className="font-mono-num"
        >
          {hi.toFixed(0)}
        </text>
      </svg>
    </div>
  );
}

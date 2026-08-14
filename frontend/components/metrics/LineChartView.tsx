"use client";

import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useUnits } from "@/lib/units/UnitsProvider";
import { convertForDisplay } from "@/lib/units/convert";
import { usePrefersReducedMotion } from "@/lib/utils/usePrefersReducedMotion";
import type { MetricDefinitionOut, TelemetryReadingOut } from "@/lib/api-types";

// Real, standalone CSS custom properties (see app/globals.css) — not the
// Tailwind `--color-*` theme tokens, which @theme inline doesn't emit as
// runtime variables. Reading these lets the chart follow the active
// light/dark palette without hardcoding hex values.
const AXIS_TICK_STYLE = {
  fill: "var(--text-muted)",
  fontFamily: "var(--font-mono)",
  fontSize: 11,
};

export function LineChartView({
  metric,
  readings,
}: {
  metric: MetricDefinitionOut;
  readings: TelemetryReadingOut[];
}) {
  const { system } = useUnits();
  const reduceMotion = usePrefersReducedMotion();

  const data = useMemo(() => {
    return [...readings]
      .sort((a, b) => a.recorded_at.localeCompare(b.recorded_at))
      .map((r) => {
        const { value, unit } = convertForDisplay(r.value, metric.unit, system);
        return { time: r.recorded_at, value: Math.round(value * 100) / 100, unit };
      });
  }, [readings, metric.unit, system]);

  const displayUnit = data[0]?.unit ?? metric.unit ?? "";

  if (data.length === 0) {
    return <p className="text-sm text-text-muted">No readings yet.</p>;
  }

  return (
    <div className="h-48 w-full" role="img" aria-label={`${metric.display_name} over time`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="time"
            tickFormatter={(t: string) =>
              new Date(t).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
            }
            tick={AXIS_TICK_STYLE}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
            minTickGap={32}
          />
          <YAxis
            tick={AXIS_TICK_STYLE}
            axisLine={false}
            tickLine={false}
            width={48}
            tickFormatter={(v: number) => `${v}${displayUnit}`}
          />
          <Tooltip
            contentStyle={{
              background: "var(--elevated)",
              border: "none",
              borderRadius: "var(--radius-surface)",
              fontFamily: "var(--font-mono)",
              fontSize: 12,
            }}
            labelStyle={{ color: "var(--text-muted)" }}
            itemStyle={{ color: "var(--text-primary)" }}
            labelFormatter={(t) => (t ? new Date(String(t)).toLocaleString() : "")}
            formatter={(value) => [`${value}${displayUnit}`, metric.display_name]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--accent-secondary)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={!reduceMotion}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

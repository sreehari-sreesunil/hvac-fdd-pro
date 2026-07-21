"use client";

import { useUnits } from "@/lib/units/UnitsProvider";
import { MonoValue } from "@/components/ui/MonoValue";
import type { MetricDefinitionOut } from "@/lib/api-types";

export function MetricRow({
  metric,
  value,
}: {
  metric: MetricDefinitionOut;
  value: number | null;
}) {
  const { formatValue } = useUnits();

  return (
    <div className="flex items-center justify-between border-b border-border py-2 last:border-b-0">
      <span className="text-sm text-text-muted">{metric.display_name}</span>
      {value === null ? (
        <span className="text-sm text-text-muted">—</span>
      ) : (
        <MonoValue className="text-sm font-medium text-text-primary">
          {formatValue(value, metric.unit)}
        </MonoValue>
      )}
    </div>
  );
}

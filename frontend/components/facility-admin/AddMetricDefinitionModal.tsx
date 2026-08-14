"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createMetricDefinition } from "@/lib/api/assets";
import { ApiError } from "@/lib/api-client";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { FormField, Input, Select } from "@/components/ui/FormField";
import { useToast } from "@/components/ui/Toast";

/**
 * Adds a metric definition for a raw metric a trained model requires but
 * the asset's asset type doesn't define yet. `metricName` is fixed (it has
 * to match the model's required_raw_metrics string exactly), so only the
 * display/unit/chart fields are editable.
 */
export function AddMetricDefinitionModal({
  open,
  onClose,
  assetTypeId,
  metricName,
}: {
  open: boolean;
  onClose: () => void;
  assetTypeId: string;
  metricName: string;
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [displayName, setDisplayName] = useState(metricName);
  const [unit, setUnit] = useState("");
  const [chartType, setChartType] = useState("line");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createMetricDefinition(assetTypeId, {
        metric_name: metricName,
        display_name: displayName,
        unit: unit || undefined,
        chart_type: chartType,
      });
      // Partial key match (qk.assetTypes now requires an org id, which this
      // single-purpose modal doesn't have in scope) - invalidates every
      // cached asset-types query regardless of which org it was fetched for.
      await queryClient.invalidateQueries({ queryKey: ["asset-types"] });
      showToast("Metric definition added");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add metric definition">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <FormField label="Raw metric key" htmlFor="add-metric-name">
          <Input id="add-metric-name" value={metricName} disabled />
        </FormField>
        <FormField label="Display name" htmlFor="add-metric-display-name">
          <Input
            id="add-metric-display-name"
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </FormField>
        <FormField label="Unit (optional)" htmlFor="add-metric-unit">
          <Input id="add-metric-unit" value={unit} onChange={(e) => setUnit(e.target.value)} />
        </FormField>
        <FormField label="Chart type" htmlFor="add-metric-chart-type">
          <Select
            id="add-metric-chart-type"
            value={chartType}
            onChange={(e) => setChartType(e.target.value)}
          >
            <option value="line">Line</option>
            <option value="gauge">Gauge</option>
            <option value="kpi">KPI</option>
          </Select>
        </FormField>
        {error && <p className="text-sm text-accent-critical-ink">{error}</p>}
        <Button type="submit" disabled={submitting} className="self-start">
          {submitting ? "Adding…" : "Add metric"}
        </Button>
      </form>
    </Modal>
  );
}

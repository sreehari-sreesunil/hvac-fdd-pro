"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createMetricMapping, listUnmappedKeys } from "@/lib/api/telemetry";
import { qk } from "@/lib/query/keys";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/FormField";
import { useToast } from "@/components/ui/Toast";
import type { MetricDefinitionOut } from "@/lib/api-types";

function MappingRow({
  assetId,
  externalKey,
  metrics,
}: {
  assetId: string;
  externalKey: string;
  metrics: MetricDefinitionOut[];
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [metricDefinitionId, setMetricDefinitionId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit() {
    if (!metricDefinitionId) return;
    setError(null);
    setSubmitting(true);
    try {
      await createMetricMapping({
        asset_id: assetId,
        external_key: externalKey,
        metric_definition_id: metricDefinitionId,
      });
      await queryClient.invalidateQueries({ queryKey: qk.unmappedKeys(assetId) });
      await queryClient.invalidateQueries({ queryKey: qk.telemetry(assetId) });
      showToast("Metric mapped");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't map this key.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 border-b border-border py-3 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
      <code className="font-mono-num text-sm text-text-primary">{externalKey}</code>
      <div className="flex items-center gap-2">
        <Select
          aria-label={`Map ${externalKey} to a metric`}
          value={metricDefinitionId}
          onChange={(e) => setMetricDefinitionId(e.target.value)}
        >
          <option value="">Select a metric…</option>
          {metrics.map((m) => (
            <option key={m.id} value={m.id}>
              {m.display_name}
            </option>
          ))}
        </Select>
        <Button size="sm" onClick={onSubmit} disabled={!metricDefinitionId || submitting}>
          {submitting ? "Mapping…" : "Map"}
        </Button>
      </div>
      {error && <p className="text-xs text-accent-critical-ink">{error}</p>}
    </div>
  );
}

export function MetricMappingPanel({
  assetId,
  metrics,
}: {
  assetId: string;
  metrics: MetricDefinitionOut[];
}) {
  const unmappedQuery = useQuery({
    queryKey: qk.unmappedKeys(assetId),
    queryFn: () => listUnmappedKeys(assetId),
  });

  if (unmappedQuery.isLoading) return null;
  if (!unmappedQuery.data || unmappedQuery.data.length === 0) return null;

  return (
    <div>
      <h3 className="font-display text-base font-semibold text-text-primary">Unmapped keys</h3>
      <p className="mt-1 text-sm text-text-muted">
        These raw device keys haven&apos;t been matched to a known metric yet.
      </p>
      <div className="mt-3">
        {unmappedQuery.data.map((key) => (
          <MappingRow key={key} assetId={assetId} externalKey={key} metrics={metrics} />
        ))}
      </div>
    </div>
  );
}

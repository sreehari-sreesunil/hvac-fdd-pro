"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Radar, Plus, Link2, CheckCircle2 } from "lucide-react";
import { getAsset, listAssetTypes } from "@/lib/api/assets";
import { createMetricMapping, listMetricMappings, listUnmappedKeys } from "@/lib/api/telemetry";
import { listModels } from "@/lib/api/ml";
import { qk } from "@/lib/query/keys";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/FormField";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";
import { useToast } from "@/components/ui/Toast";
import { AssetSelector, type AssetSelectorValue } from "@/components/shared/AssetSelector";
import { AddMetricDefinitionModal } from "@/components/facility-admin/AddMetricDefinitionModal";

type MetricStatus =
  | { rawName: string; state: "mapped" }
  | { rawName: string; state: "unmapped"; metricDefinitionId: string }
  | { rawName: string; state: "missing" };

function MapMetricRow({
  assetId,
  metricDefinitionId,
  unmappedKeys,
}: {
  assetId: string;
  metricDefinitionId: string;
  unmappedKeys: string[];
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [externalKey, setExternalKey] = useState("");

  const mapMutation = useMutation({
    mutationFn: () =>
      createMetricMapping({ asset_id: assetId, external_key: externalKey, metric_definition_id: metricDefinitionId }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: qk.metricMappings(assetId) });
      await queryClient.invalidateQueries({ queryKey: qk.unmappedKeys(assetId) });
      showToast("Sensor key mapped");
    },
    onError: (err) => {
      showToast(err instanceof ApiError ? err.message : "Couldn't map this key.", "error");
    },
  });

  if (unmappedKeys.length === 0) {
    return <span className="text-xs text-text-muted">No unmapped keys available to map yet.</span>;
  }

  return (
    <div className="flex items-center gap-2">
      <Select
        aria-label="Choose a raw sensor key"
        value={externalKey}
        onChange={(e) => setExternalKey(e.target.value)}
      >
        <option value="">Select a raw key…</option>
        {unmappedKeys.map((key) => (
          <option key={key} value={key}>
            {key}
          </option>
        ))}
      </Select>
      <Button
        size="sm"
        onClick={() => mapMutation.mutate()}
        disabled={!externalKey || mapMutation.isPending}
      >
        <Link2 size={14} strokeWidth={1.75} />
        {mapMutation.isPending ? "Mapping…" : "Map"}
      </Button>
    </div>
  );
}

export default function SensorReadinessPage() {
  const [selection, setSelection] = useState<AssetSelectorValue>({
    facilityId: null,
    assetId: null,
  });
  const [addMetricFor, setAddMetricFor] = useState<string | null>(null);
  const assetId = selection.assetId;
  const { currentOrgId } = useAuth();

  const assetQuery = useQuery({
    queryKey: qk.asset(assetId ?? ""),
    queryFn: () => getAsset(assetId as string),
    enabled: !!assetId,
  });
  const assetTypesQuery = useQuery({
    queryKey: qk.assetTypes(currentOrgId ?? ""),
    queryFn: () => listAssetTypes(currentOrgId as string),
    enabled: !!currentOrgId,
  });
  const mappingsQuery = useQuery({
    queryKey: qk.metricMappings(assetId ?? ""),
    queryFn: () => listMetricMappings(assetId as string),
    enabled: !!assetId,
  });
  const unmappedKeysQuery = useQuery({
    queryKey: qk.unmappedKeys(assetId ?? ""),
    queryFn: () => listUnmappedKeys(assetId as string),
    enabled: !!assetId,
  });
  const modelsQuery = useQuery({ queryKey: qk.models(), queryFn: listModels });

  const assetType = assetTypesQuery.data?.find((t) => t.id === assetQuery.data?.asset_type_id);

  const readiness = useMemo(() => {
    if (!modelsQuery.data || !assetType) return [];
    return modelsQuery.data.map((model) => {
      const statuses: MetricStatus[] = model.required_raw_metrics.map((rawName) => {
        const metricDef = assetType.metric_definitions.find((m) => m.metric_name === rawName);
        if (!metricDef) return { rawName, state: "missing" };
        const mapped = mappingsQuery.data?.some((mm) => mm.metric_definition_id === metricDef.id);
        return mapped
          ? { rawName, state: "mapped" }
          : { rawName, state: "unmapped", metricDefinitionId: metricDef.id };
      });
      return { model, statuses, ready: statuses.every((s) => s.state === "mapped") };
    });
  }, [modelsQuery.data, assetType, mappingsQuery.data]);

  const isLoading =
    !!assetId &&
    (assetQuery.isLoading || assetTypesQuery.isLoading || mappingsQuery.isLoading || modelsQuery.isLoading);
  const isError = assetQuery.isError || assetTypesQuery.isError || mappingsQuery.isError || modelsQuery.isError;

  return (
    <div className="flex flex-col gap-8">
      <header className="border-b-2 border-text-primary pb-4">
        <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
          #05 — SENSOR READINESS
        </p>
        <h1 className="font-display text-3xl font-bold leading-none text-text-primary sm:text-4xl">
          Sensor Readiness
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-text-muted">
          For a chosen asset, compare its mapped sensors against what each trained model
          actually requires — and fix any gaps directly here.
        </p>
      </header>

      <Card>
        <AssetSelector value={selection} onChange={setSelection} />
      </Card>

      {!assetId && (
        <EmptyState
          icon={Radar}
          title="Select an asset"
          description="Choose a facility and asset above to check model readiness."
        />
      )}

      {assetId && isError && (
        <QueryErrorState
          error={assetQuery.error ?? assetTypesQuery.error ?? mappingsQuery.error ?? modelsQuery.error}
          onRetry={() => {
            assetQuery.refetch();
            assetTypesQuery.refetch();
            mappingsQuery.refetch();
            modelsQuery.refetch();
          }}
          resourceLabel="sensor readiness data"
        />
      )}

      {assetId && !isError && isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      )}

      {assetId && !isError && !isLoading && readiness.length === 0 && (
        <EmptyState
          icon={Radar}
          title="No trained models found"
          description="There are no models to check readiness against yet."
        />
      )}

      {assetId && !isError && !isLoading && readiness.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {readiness.map(({ model, statuses, ready }) => (
            <Card key={model.model_name}>
              <CardHeader>
                <CardTitle>{model.model_name}</CardTitle>
                <Badge tone={ready ? "primary" : "critical"} icon={ready ? CheckCircle2 : undefined}>
                  {ready ? "Ready" : "Not ready"}
                </Badge>
              </CardHeader>

              {(model.algorithm || model.dataset) && (
                <p className="mb-3 font-mono text-xs uppercase tracking-wide text-text-subtle">
                  {[model.algorithm, model.dataset].filter(Boolean).join(" · ")}
                </p>
              )}

              <div className="flex flex-col gap-3">
                {statuses.map((status) => (
                  <div
                    key={status.rawName}
                    className="flex flex-col gap-2 rounded-structural border border-border p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <code className="font-mono-num text-sm text-text-primary">
                        {status.rawName}
                      </code>
                      <Badge
                        tone={
                          status.state === "mapped"
                            ? "primary"
                            : status.state === "unmapped"
                              ? "warning"
                              : "critical"
                        }
                      >
                        {status.state}
                      </Badge>
                    </div>

                    {status.state === "missing" && (
                      <Button
                        variant="secondary"
                        size="sm"
                        className="self-start"
                        onClick={() => setAddMetricFor(status.rawName)}
                      >
                        <Plus size={14} strokeWidth={1.75} />
                        Add metric
                      </Button>
                    )}

                    {status.state === "unmapped" && (
                      <MapMetricRow
                        assetId={assetId}
                        metricDefinitionId={status.metricDefinitionId}
                        unmappedKeys={unmappedKeysQuery.data ?? []}
                      />
                    )}
                  </div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}

      {assetType && (
        <AddMetricDefinitionModal
          open={!!addMetricFor}
          onClose={() => setAddMetricFor(null)}
          assetTypeId={assetType.id}
          metricName={addMetricFor ?? ""}
        />
      )}
    </div>
  );
}

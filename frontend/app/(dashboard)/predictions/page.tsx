"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Brain, Play, Sparkles, Target, AlertTriangle, CheckCircle2 } from "lucide-react";
import { explainPrediction, getAttributedFault, getPrediction, listModels } from "@/lib/api/ml";
import { qk } from "@/lib/query/keys";
import { ApiError } from "@/lib/api-client";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/FormField";
import { MonoValue } from "@/components/ui/MonoValue";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";
import { AssetSelector, type AssetSelectorValue } from "@/components/shared/AssetSelector";
import type { PredictionOut } from "@/lib/api-types";

function isClassifierResult(p: PredictionOut) {
  return p.fault_probability !== undefined;
}

function PredictSection({ assetId, modelNames }: { assetId: string; modelNames: string[] }) {
  const [modelName, setModelName] = useState(modelNames[0] ?? "");

  const mutation = useMutation({
    mutationFn: () => getPrediction(assetId, modelName),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Predict</CardTitle>
      </CardHeader>
      <div className="flex flex-col gap-4">
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Select
              aria-label="Model to run"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            >
              {modelNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </Select>
          </div>
          <Button
            size="sm"
            onClick={() => mutation.mutate()}
            disabled={!modelName || mutation.isPending}
          >
            <Play size={14} strokeWidth={1.75} />
            {mutation.isPending ? "Running…" : "Run prediction"}
          </Button>
        </div>

        {mutation.isError && (
          <p className="text-sm text-accent-critical-ink">
            {mutation.error instanceof ApiError ? mutation.error.message : "Prediction failed."}
          </p>
        )}

        {mutation.data && (
          <div className="flex flex-col gap-3 rounded-surface bg-neo-base p-4 shadow-neo-resting">
            {isClassifierResult(mutation.data) ? (
              <>
                <div className="flex items-center gap-2">
                  <Badge tone={mutation.data.predicted_label === 1 ? "critical" : "primary"}>
                    {mutation.data.predicted_label === 1 ? "Fault predicted" : "Nominal"}
                  </Badge>
                  {mutation.data.confidence && (
                    <Badge tone="neutral">{mutation.data.confidence} confidence</Badge>
                  )}
                </div>
                <div className="flex items-baseline gap-1">
                  <MonoValue as="div" className="text-2xl font-semibold text-text-primary">
                    {((mutation.data.fault_probability ?? 0) * 100).toFixed(1)}
                  </MonoValue>
                  <span className="text-sm text-text-muted">% fault probability</span>
                </div>
              </>
            ) : (
              <>
                <Badge tone={mutation.data.is_anomaly ? "critical" : "primary"}>
                  {mutation.data.is_anomaly ? "Anomaly detected" : "Normal"}
                </Badge>
                <div className="flex items-baseline gap-1">
                  <MonoValue as="div" className="text-2xl font-semibold text-text-primary">
                    {(mutation.data.anomaly_score ?? 0).toFixed(3)}
                  </MonoValue>
                  <span className="text-sm text-text-muted">anomaly score</span>
                </div>
              </>
            )}
            {mutation.data.notes && (
              <p className="text-xs text-text-muted">{mutation.data.notes}</p>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

function AttributeSection({ assetId, modelNames }: { assetId: string; modelNames: string[] }) {
  const [selected, setSelected] = useState<Set<string>>(() => new Set(modelNames));

  const mutation = useMutation({
    mutationFn: () => getAttributedFault(assetId, Array.from(selected)),
  });

  function toggle(name: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Attribute</CardTitle>
        <span className="font-mono text-xs uppercase tracking-wide text-text-muted">
          Cross-classifier argmax
        </span>
      </CardHeader>

      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-3">
          {modelNames.map((name) => (
            <label key={name} className="flex items-center gap-2 text-sm text-text-primary">
              <input
                type="checkbox"
                checked={selected.has(name)}
                onChange={() => toggle(name)}
              />
              <span className="font-mono-num text-xs">{name}</span>
            </label>
          ))}
        </div>

        <Button
          size="sm"
          className="self-start"
          onClick={() => mutation.mutate()}
          disabled={selected.size === 0 || mutation.isPending}
        >
          <Target size={14} strokeWidth={1.75} />
          {mutation.isPending ? "Diagnosing…" : "Run diagnosis"}
        </Button>

        {mutation.isError && (
          <p className="text-sm text-accent-critical-ink">
            {mutation.error instanceof ApiError ? mutation.error.message : "Attribution failed."}
          </p>
        )}

        {mutation.data && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-3 rounded-surface bg-neo-base p-4 shadow-neo-resting">
              <Badge
                tone={mutation.data.fault_detected ? "critical" : "primary"}
                icon={mutation.data.fault_detected ? AlertTriangle : CheckCircle2}
              >
                {mutation.data.fault_detected ? "Fault detected" : "No fault detected"}
              </Badge>
              {mutation.data.fault_detected && mutation.data.attributed_model && (
                <span className="text-sm text-text-primary">
                  Attributed to{" "}
                  <span className="font-mono-num text-accent-glow-ink">
                    {mutation.data.attributed_model}
                  </span>{" "}
                  (
                  {((mutation.data.attributed_fault_probability ?? 0) * 100).toFixed(1)}%)
                </span>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-text-muted">
                    <th className="py-2 pr-4 font-medium">Model</th>
                    <th className="py-2 pr-4 font-medium">Label</th>
                    <th className="py-2 pr-4 font-medium">Probability</th>
                    <th className="py-2 font-medium">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {mutation.data.all_results.map((r) => (
                    <tr key={r.model_name} className="border-b border-border last:border-b-0">
                      <td className="py-2 pr-4 font-mono-num text-text-primary">{r.model_name}</td>
                      <td className="py-2 pr-4">
                        <Badge tone={r.predicted_label === 1 ? "critical" : "primary"}>
                          {r.predicted_label === 1 ? "fault" : "ok"}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4">
                        <MonoValue className="text-text-primary">
                          {(r.fault_probability * 100).toFixed(1)}%
                        </MonoValue>
                      </td>
                      <td className="py-2 text-text-muted">{r.confidence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {mutation.data.models_skipped.length > 0 && (
              <div className="flex flex-col gap-1">
                <p className="font-mono text-xs uppercase tracking-wide text-text-muted">
                  Skipped
                </p>
                {mutation.data.models_skipped.map((s) => (
                  <p key={s.model_name} className="text-xs text-text-muted">
                    <span className="font-mono-num">{s.model_name}</span> — {s.reason}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

function ExplainSection({ assetId, modelNames }: { assetId: string; modelNames: string[] }) {
  const [modelName, setModelName] = useState(modelNames[0] ?? "");

  const mutation = useMutation({
    mutationFn: () => explainPrediction(assetId, modelName),
  });

  const contributions = mutation.data?.feature_contributions ?? [];
  const maxMagnitude = Math.max(1e-9, ...contributions.map((c) => Math.abs(c.shap_contribution)));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Explain</CardTitle>
        <span className="font-mono text-xs uppercase tracking-wide text-text-muted">
          SHAP feature importance
        </span>
      </CardHeader>

      <div className="flex flex-col gap-4">
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Select
              aria-label="Model to explain"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            >
              {modelNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </Select>
          </div>
          <Button
            size="sm"
            onClick={() => mutation.mutate()}
            disabled={!modelName || mutation.isPending}
          >
            <Sparkles size={14} strokeWidth={1.75} />
            {mutation.isPending ? "Explaining…" : "Explain"}
          </Button>
        </div>

        {mutation.isError && (
          <p className="text-sm text-accent-critical-ink">
            {mutation.error instanceof ApiError ? mutation.error.message : "Explanation failed."}
          </p>
        )}

        {mutation.data?.error && (
          <p className="text-sm text-text-muted">{mutation.data.error}</p>
        )}

        {contributions.length > 0 && (
          <div className="flex flex-col gap-2">
            {contributions.map((c) => {
              const widthPct = (Math.abs(c.shap_contribution) / maxMagnitude) * 100;
              return (
                <div key={c.feature} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-mono-num text-xs text-text-primary">
                      {c.feature}
                    </span>
                    <MonoValue className="text-xs text-text-muted">
                      {c.shap_contribution > 0 ? "+" : ""}
                      {c.shap_contribution.toFixed(3)}
                    </MonoValue>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-elevated">
                    <div
                      className="h-full rounded-full bg-accent-glow shadow-[0_0_6px_var(--accent-glow)]"
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

export default function PredictionsPage() {
  const [selection, setSelection] = useState<AssetSelectorValue>({
    facilityId: null,
    assetId: null,
  });
  const assetId = selection.assetId;

  const modelsQuery = useQuery({ queryKey: qk.models(), queryFn: listModels });
  const modelNames = modelsQuery.data?.map((m) => m.model_name) ?? [];

  return (
    <div className="flex flex-col gap-8">
      <header className="border-b-2 border-text-primary pb-4">
        <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
          #06 — FAULT DIAGNOSIS
        </p>
        <h1 className="font-display text-3xl font-bold leading-none text-text-primary sm:text-4xl">
          Predictions
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-text-muted">
          Run a classifier, attribute a fault across multiple models via argmax, and inspect
          the SHAP feature importance behind any prediction.
        </p>
      </header>

      <Card>
        <AssetSelector value={selection} onChange={setSelection} />
      </Card>

      {!assetId && (
        <EmptyState
          icon={Brain}
          title="Select an asset"
          description="Choose a facility and asset above to run diagnostics."
        />
      )}

      {assetId && modelsQuery.isError && (
        <QueryErrorState
          error={modelsQuery.error}
          onRetry={() => modelsQuery.refetch()}
          resourceLabel="the model list"
        />
      )}

      {assetId && !modelsQuery.isError && modelsQuery.isLoading && (
        <div className="grid grid-cols-1 gap-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      )}

      {assetId && !modelsQuery.isError && !modelsQuery.isLoading && modelNames.length === 0 && (
        <EmptyState
          icon={Brain}
          title="No trained models available"
          description="There are no models in the registry yet."
        />
      )}

      {assetId && modelNames.length > 0 && (
        <div className="flex flex-col gap-6">
          <PredictSection assetId={assetId} modelNames={modelNames} />
          <AttributeSection assetId={assetId} modelNames={modelNames} />
          <ExplainSection assetId={assetId} modelNames={modelNames} />
        </div>
      )}
    </div>
  );
}

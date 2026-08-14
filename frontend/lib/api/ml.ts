import { apiFetch } from "@/lib/api-client";
import type { AttributedFaultOut, ExplainOut, ModelInfoOut, PredictionOut } from "@/lib/api-types";

export function listModels() {
  return apiFetch<ModelInfoOut[]>("ml", "/models");
}

export function getPrediction(assetId: string, modelName: string) {
  return apiFetch<PredictionOut>(
    "ml",
    `/predictions/${assetId}?model_name=${encodeURIComponent(modelName)}`,
  );
}

export function getAttributedFault(assetId: string, modelNames: string[]) {
  const params = new URLSearchParams();
  for (const name of modelNames) params.append("model_names", name);
  return apiFetch<AttributedFaultOut>(
    "ml",
    `/predictions/${assetId}/attribute?${params.toString()}`,
  );
}

export function explainPrediction(assetId: string, modelName: string) {
  return apiFetch<ExplainOut>(
    "ml",
    `/predictions/${assetId}/explain?model_name=${encodeURIComponent(modelName)}`,
  );
}

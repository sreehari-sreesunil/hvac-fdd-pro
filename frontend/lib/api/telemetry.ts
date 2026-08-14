import { apiFetch } from "@/lib/api-client";
import type {
  EdgeDeviceOut,
  IngestionKeyCreateOut,
  MetricMappingCreateResponse,
  MetricMappingOut,
  TelemetryCsvUploadResponse,
  TelemetryReadingBulkCreateResponse,
  TelemetryReadingOut,
} from "@/lib/api-types";

export function createEdgeDevice(body: { facility_id: string; name: string }) {
  return apiFetch<EdgeDeviceOut>("telemetry", "/edge-devices", { method: "POST", body });
}

export function issueIngestionKey(deviceId: string) {
  return apiFetch<IngestionKeyCreateOut>("telemetry", `/edge-devices/${deviceId}/keys`, {
    method: "POST",
  });
}

export function listTelemetry(assetId: string, metricDefinitionId?: string) {
  const params = new URLSearchParams({ asset_id: assetId });
  if (metricDefinitionId) params.set("metric_definition_id", metricDefinitionId);
  return apiFetch<TelemetryReadingOut[]>("telemetry", `/telemetry?${params.toString()}`);
}

export function listUnmappedKeys(assetId: string) {
  return apiFetch<string[]>(
    "telemetry",
    `/telemetry/unmapped?asset_id=${encodeURIComponent(assetId)}`,
  );
}

export function listMetricMappings(assetId: string) {
  return apiFetch<MetricMappingOut[]>(
    "telemetry",
    `/metric-mappings?asset_id=${encodeURIComponent(assetId)}`,
  );
}

export function createMetricMapping(body: {
  asset_id: string;
  external_key: string;
  metric_definition_id: string;
}) {
  return apiFetch<MetricMappingCreateResponse>("telemetry", "/metric-mappings", {
    method: "POST",
    body,
  });
}

export function uploadTelemetryCsv(ingestionKey: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<TelemetryCsvUploadResponse>("telemetry", "/telemetry/csv-upload", {
    method: "POST",
    body: formData,
    auth: false,
    headers: { "X-Ingestion-Key": ingestionKey },
  });
}

export function uploadTelemetryBulk(
  ingestionKey: string,
  readings: { asset_id: string; external_key: string; value: number; recorded_at: string }[],
) {
  return apiFetch<TelemetryReadingBulkCreateResponse>("telemetry", "/telemetry/bulk", {
    method: "POST",
    body: { readings },
    auth: false,
    headers: { "X-Ingestion-Key": ingestionKey },
  });
}

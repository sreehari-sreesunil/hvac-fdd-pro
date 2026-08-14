import { apiFetch } from "@/lib/api-client";
import type { AssetOut, AssetTypeOut, FacilityOut, MetricDefinitionCreate, MetricDefinitionOut } from "@/lib/api-types";

export function createFacility(body: {
  organization_id: string;
  name: string;
  address?: string;
  timezone?: string;
}) {
  return apiFetch<FacilityOut>("asset", "/facilities", { method: "POST", body });
}

export function listFacilities(organizationId: string) {
  return apiFetch<FacilityOut[]>(
    "asset",
    `/facilities?organization_id=${encodeURIComponent(organizationId)}`,
  );
}

export function getFacility(facilityId: string) {
  return apiFetch<FacilityOut>("asset", `/facilities/${facilityId}`);
}

export function createAssetType(body: {
  organization_id: string;
  name: string;
  description?: string;
  metrics?: {
    metric_name: string;
    display_name: string;
    unit?: string;
    datatype?: string;
    chart_type?: string;
  }[];
}) {
  return apiFetch<AssetTypeOut>("asset", "/asset-types", { method: "POST", body });
}

export function listAssetTypes(organizationId: string) {
  return apiFetch<AssetTypeOut[]>(
    "asset",
    `/asset-types?organization_id=${encodeURIComponent(organizationId)}`,
  );
}

export function createAsset(body: {
  facility_id: string;
  asset_type_id: string;
  name: string;
  external_ref?: string;
}) {
  return apiFetch<AssetOut>("asset", "/assets", { method: "POST", body });
}

export function listAssets(facilityId: string) {
  return apiFetch<AssetOut[]>("asset", `/assets?facility_id=${encodeURIComponent(facilityId)}`);
}

export function getAsset(assetId: string) {
  return apiFetch<AssetOut>("asset", `/assets/${assetId}`);
}

export function createMetricDefinition(assetTypeId: string, body: MetricDefinitionCreate) {
  return apiFetch<MetricDefinitionOut>("asset", `/asset-types/${assetTypeId}/metrics`, {
    method: "POST",
    body,
  });
}

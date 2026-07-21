export const qk = {
  organizations: () => ["organizations"] as const,
  facilities: (orgId: string) => ["facilities", orgId] as const,
  facility: (facilityId: string) => ["facility", facilityId] as const,
  assets: (facilityId: string) => ["assets", facilityId] as const,
  asset: (assetId: string) => ["asset", assetId] as const,
  assetTypes: () => ["asset-types"] as const,
  telemetry: (assetId: string, metricDefinitionId?: string) =>
    ["telemetry", assetId, metricDefinitionId ?? null] as const,
  unmappedKeys: (assetId: string) => ["unmapped-keys", assetId] as const,
};

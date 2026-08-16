export const qk = {
  organizations: () => ["organizations"] as const,
  members: (orgId: string) => ["members", orgId] as const,
  facilities: (orgId: string) => ["facilities", orgId] as const,
  facility: (facilityId: string) => ["facility", facilityId] as const,
  assets: (facilityId: string) => ["assets", facilityId] as const,
  asset: (assetId: string) => ["asset", assetId] as const,
  assetTypes: (orgId: string) => ["asset-types", orgId] as const,
  telemetry: (assetId: string, metricDefinitionId?: string) =>
    ["telemetry", assetId, metricDefinitionId ?? null] as const,
  unmappedKeys: (assetId: string) => ["unmapped-keys", assetId] as const,
  metricMappings: (assetId: string) => ["metric-mappings", assetId] as const,
  alerts: (assetId: string, status?: string) => ["alerts", assetId, status ?? null] as const,
  report: (facilityId: string, period: string, date?: string) =>
    ["report", facilityId, period, date ?? null] as const,
  models: () => ["models"] as const,
  prediction: (assetId: string, modelName: string) => ["prediction", assetId, modelName] as const,
  attribution: (assetId: string, modelNames: string[]) =>
    ["attribution", assetId, ...modelNames] as const,
  explanation: (assetId: string, modelName: string) => ["explanation", assetId, modelName] as const,
};

// Types mirror the confirmed backend response shapes verbatim.

export type Role = "admin" | "operator" | "viewer";

// ---- auth-service ----

export type UserOut = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type OrganizationOut = {
  id: string;
  name: string;
  created_at: string;
  role: Role;
};

export type InviteResponse = {
  detail: string;
  user_id: string;
  role: Role;
};

// ---- asset-service ----

export type FacilityOut = {
  id: string;
  organization_id: string;
  name: string;
  address: string | null;
  timezone: string;
};

export type ChartType = "line" | "gauge" | "kpi";

export type MetricDefinitionOut = {
  id: string;
  asset_type_id: string;
  metric_name: string;
  display_name: string;
  unit: string | null;
  datatype: string;
  chart_type: string;
  min_value: number | null;
  max_value: number | null;
};

export type AssetTypeOut = {
  id: string;
  name: string;
  description: string | null;
  metric_definitions: MetricDefinitionOut[];
};

export type AssetOut = {
  id: string;
  facility_id: string;
  asset_type_id: string;
  name: string;
  external_ref: string | null;
  created_at: string;
};

// ---- telemetry-service ----

export type EdgeDeviceOut = {
  id: string;
  facility_id: string;
  name: string;
  last_seen_at: string | null;
  deactivated_at: string | null;
  created_at: string;
};

export type IngestionKeyCreateOut = {
  id: string;
  edge_device_id: string;
  api_key: string;
  key_prefix: string;
  created_at: string;
};

export type TelemetryReadingOut = {
  id: string;
  asset_id: string;
  external_key: string;
  metric_definition_id: string | null;
  value: number;
  recorded_at: string;
  ingested_at: string;
  source_type: string;
  idempotency_key: string | null;
};

export type MetricMappingOut = {
  id: string;
  asset_id: string;
  external_key: string;
  metric_definition_id: string;
  created_at: string;
};

export type MetricMappingCreateResponse = {
  mapping: MetricMappingOut;
  backfilled_count: number;
};

export type CsvRowError = {
  row: number;
  error: string;
};

export type TelemetryCsvUploadResponse = {
  accepted_count: number;
  unmapped_count: number;
  duplicate_count: number;
  invalid_rows: CsvRowError[];
};

export type TelemetryReadingBulkCreateResponse = {
  accepted_count: number;
  unmapped_count: number;
  duplicate_count: number;
};

// ---- copilot-service ----

export type ChatRequest = {
  message: string;
  conversation_id?: string | null;
};

export type ChatResponse = {
  answer: string;
  conversation_id: string;
  sources_used: string[];
  tools_called: string[];
  retrieved_context: string[];
};

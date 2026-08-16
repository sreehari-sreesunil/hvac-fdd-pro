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

export type MemberOut = {
  user_id: string;
  email: string;
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

export type MetricDefinitionCreate = {
  metric_name: string;
  display_name: string;
  unit?: string;
  datatype?: string;
  chart_type?: string;
  min_value?: number | null;
  max_value?: number | null;
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

// ---- notification-service ----

export type AlertSeverity = "warning" | "critical";
export type AlertStatus = "open" | "acknowledged" | "resolved";

export type AlertOut = {
  id: string;
  asset_id: string;
  metric_definition_id: string | null;
  source: string;
  severity: string;
  status: string;
  message: string;
  details: Record<string, unknown> | null;
  created_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
};

export type ReportPeriod = "daily" | "weekly" | "monthly";

export type ReportAlertsSummary = {
  total: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
};

export type ReportAssetSummary = {
  asset_id: string;
  asset_name: string;
  alert_count: number;
  ingestion_count: number;
};

export type FacilityReportOut = {
  facility_id: string;
  period: string;
  start: string;
  end: string;
  asset_count: number;
  alerts: ReportAlertsSummary;
  per_asset: ReportAssetSummary[];
};

// ---- ml-service ----

export type ModelInfoOut = {
  model_name: string;
  required_raw_metrics: string[];
  status: string | null;
  algorithm: string | null;
  dataset: string | null;
};

/** GET /predictions/{asset_id} has no fixed response_model — the backend
 *  returns a classifier shape (predicted_label/fault_probability/confidence)
 *  or an anomaly-detector shape (is_anomaly/anomaly_score), discriminated by
 *  which fields are present, never both. */
export type PredictionOut = {
  model: string;
  status: string;
  notes: string;
  feature_values: Record<string, number>;
  predicted_label?: number;
  fault_probability?: number;
  confidence?: "high" | "moderate" | "low";
  is_anomaly?: boolean;
  anomaly_score?: number;
};

export type SkippedModel = {
  model_name: string;
  reason: string;
};

export type ClassifierResult = {
  model_name: string;
  predicted_label: number;
  fault_probability: number;
  confidence: string;
};

export type AttributedFaultOut = {
  asset_id: string;
  models_evaluated: string[];
  models_skipped: SkippedModel[];
  fault_detected: boolean;
  attributed_model: string | null;
  attributed_fault_probability: number | null;
  all_results: ClassifierResult[];
};

export type FeatureContribution = {
  feature: string;
  value: number;
  shap_contribution: number;
};

/** GET /predictions/{asset_id}/explain also has no fixed response_model —
 *  the Isolation Forest anomaly gatekeeper returns {model, error} instead
 *  of {model, feature_contributions} since SHAP doesn't support it. */
export type ExplainOut = {
  model: string;
  feature_contributions?: FeatureContribution[];
  error?: string;
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

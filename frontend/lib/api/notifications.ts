import { apiFetch } from "@/lib/api-client";
import type { AlertOut, FacilityReportOut, ReportPeriod } from "@/lib/api-types";

export function listAlerts(
  assetId: string,
  filters?: { status?: string; severity?: string },
) {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.severity) params.set("severity", filters.severity);
  const query = params.toString();
  return apiFetch<AlertOut[]>("notification", `/alerts/${assetId}${query ? `?${query}` : ""}`);
}

export function acknowledgeAlert(assetId: string, alertId: string) {
  return apiFetch<AlertOut>("notification", `/alerts/${assetId}/${alertId}/acknowledge`, {
    method: "PATCH",
  });
}

export function resolveAlert(assetId: string, alertId: string) {
  return apiFetch<AlertOut>("notification", `/alerts/${assetId}/${alertId}/resolve`, {
    method: "PATCH",
  });
}

export function getFacilityReport(facilityId: string, period: ReportPeriod, date?: string) {
  const params = new URLSearchParams({ period });
  if (date) params.set("date", date);
  return apiFetch<FacilityReportOut>(
    "notification",
    `/reports/${facilityId}?${params.toString()}`,
  );
}

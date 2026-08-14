"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileBarChart2 } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { listFacilities } from "@/lib/api/assets";
import { getFacilityReport } from "@/lib/api/notifications";
import { qk } from "@/lib/query/keys";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { FormField, Input, Select } from "@/components/ui/FormField";
import { MonoValue } from "@/components/ui/MonoValue";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";
import type { ReportPeriod } from "@/lib/api-types";

const PERIODS: ReportPeriod[] = ["daily", "weekly", "monthly"];

export default function ReportsPage() {
  const { currentOrgId } = useAuth();
  const [facilityId, setFacilityId] = useState("");
  const [period, setPeriod] = useState<ReportPeriod>("weekly");
  const [date, setDate] = useState("");

  const facilitiesQuery = useQuery({
    queryKey: qk.facilities(currentOrgId ?? ""),
    queryFn: () => listFacilities(currentOrgId as string),
    enabled: !!currentOrgId,
  });

  const reportQuery = useQuery({
    queryKey: qk.report(facilityId, period, date || undefined),
    queryFn: () => getFacilityReport(facilityId, period, date || undefined),
    enabled: !!facilityId,
  });

  const report = reportQuery.data;

  return (
    <div className="flex flex-col gap-8">
      <header className="border-b-2 border-text-primary pb-4">
        <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
          #04 — REPORTS
        </p>
        <h1 className="font-display text-3xl font-bold leading-none text-text-primary sm:text-4xl">
          Reports
        </h1>
      </header>

      <Card>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <FormField label="Facility" htmlFor="report-facility">
            {facilitiesQuery.isLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <Select
                id="report-facility"
                value={facilityId}
                onChange={(e) => setFacilityId(e.target.value)}
              >
                <option value="">Select a facility…</option>
                {facilitiesQuery.data?.map((facility) => (
                  <option key={facility.id} value={facility.id}>
                    {facility.name}
                  </option>
                ))}
              </Select>
            )}
          </FormField>

          <FormField label="Period" htmlFor="report-period">
            <Select
              id="report-period"
              value={period}
              onChange={(e) => setPeriod(e.target.value as ReportPeriod)}
            >
              {PERIODS.map((p) => (
                <option key={p} value={p}>
                  {p[0].toUpperCase() + p.slice(1)}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField label="Anchor date (optional)" htmlFor="report-date">
            <Input
              id="report-date"
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </FormField>
        </div>
      </Card>

      {!facilityId && (
        <EmptyState
          icon={FileBarChart2}
          title="Select a facility"
          description="Choose a facility and period above to generate a report."
        />
      )}

      {facilityId && reportQuery.isError && (
        <QueryErrorState
          error={reportQuery.error}
          onRetry={() => reportQuery.refetch()}
          resourceLabel="this report"
        />
      )}

      {facilityId && !reportQuery.isError && reportQuery.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      )}

      {report && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-surface bg-neo-base p-4 shadow-neo-resting">
              <p className="font-mono text-xs uppercase tracking-wide text-text-muted">
                Total alerts
              </p>
              <MonoValue as="div" className="text-3xl font-semibold text-text-primary">
                {report.alerts.total}
              </MonoValue>
            </div>
            <div className="rounded-surface bg-neo-base p-4 shadow-neo-resting">
              <p className="font-mono text-xs uppercase tracking-wide text-text-muted">Assets</p>
              <MonoValue as="div" className="text-3xl font-semibold text-text-primary">
                {report.asset_count}
              </MonoValue>
            </div>
            <div className="flex flex-col gap-2 rounded-surface bg-neo-base p-4 shadow-neo-resting">
              <p className="font-mono text-xs uppercase tracking-wide text-text-muted">
                By severity
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(report.alerts.by_severity).length === 0 && (
                  <span className="text-sm text-text-muted">None</span>
                )}
                {Object.entries(report.alerts.by_severity).map(([severity, count]) => (
                  <Badge key={severity} tone={severity === "critical" ? "critical" : "warning"}>
                    {severity}: {count}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Per-asset breakdown</CardTitle>
              <span className="font-mono-num text-xs text-text-muted">
                {new Date(report.start).toLocaleDateString()} –{" "}
                {new Date(report.end).toLocaleDateString()}
              </span>
            </CardHeader>

            {report.per_asset.length === 0 ? (
              <p className="text-sm text-text-muted">No assets in this facility.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-text-muted">
                      <th className="py-2 pr-4 font-medium">Asset</th>
                      <th className="py-2 pr-4 font-medium">Alerts</th>
                      <th className="py-2 font-medium">Readings ingested</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.per_asset.map((asset) => (
                      <tr key={asset.asset_id} className="border-b border-border last:border-b-0">
                        <td className="py-2 pr-4 text-text-primary">{asset.asset_name}</td>
                        <td className="py-2 pr-4">
                          <MonoValue className="text-text-primary">{asset.alert_count}</MonoValue>
                        </td>
                        <td className="py-2">
                          <MonoValue className="text-text-primary">
                            {asset.ingestion_count.toLocaleString()}
                          </MonoValue>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

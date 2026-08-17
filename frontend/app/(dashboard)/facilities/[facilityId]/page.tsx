"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cpu, KeyRound, Plus, Radio, Upload } from "lucide-react";
import { getFacility, listAssets } from "@/lib/api/assets";
import { createEdgeDevice, listEdgeDevices } from "@/lib/api/telemetry";
import { qk } from "@/lib/query/keys";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ApiError } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/utils/format";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { FormField, Input } from "@/components/ui/FormField";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";
import { useToast } from "@/components/ui/Toast";
import { AssetForm } from "@/components/facility-admin/AssetForm";
import { IssueKeyDialog } from "@/components/facility-admin/IssueKeyDialog";
import { CsvUploadDialog } from "@/components/facility-admin/CsvUploadDialog";

export default function FacilityDetailPage() {
  const { facilityId } = useParams<{ facilityId: string }>();
  const { hasRole, currentOrgId } = useAuth();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const [assetModalOpen, setAssetModalOpen] = useState(false);
  const [deviceName, setDeviceName] = useState("");
  const [keyDialogDeviceId, setKeyDialogDeviceId] = useState<string | null>(null);
  const [csvUploadDeviceId, setCsvUploadDeviceId] = useState<string | null>(null);

  const facilityQuery = useQuery({
    queryKey: qk.facility(facilityId),
    queryFn: () => getFacility(facilityId),
  });
  const assetsQuery = useQuery({
    queryKey: qk.assets(facilityId),
    queryFn: () => listAssets(facilityId),
  });
  const devicesQuery = useQuery({
    queryKey: qk.edgeDevices(facilityId),
    queryFn: () => listEdgeDevices(facilityId),
  });
  const devices = devicesQuery.data ?? [];

  const canManageDevices = hasRole(["admin", "operator"]);

  const createDevice = useMutation({
    mutationFn: () => createEdgeDevice({ facility_id: facilityId, name: deviceName }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: qk.edgeDevices(facilityId) });
      setDeviceName("");
      showToast("Device added");
    },
    onError: (err) => {
      showToast(err instanceof ApiError ? err.message : "Couldn't add device.", "error");
    },
  });

  if (facilityQuery.isError) {
    return (
      <QueryErrorState
        error={facilityQuery.error}
        onRetry={() => facilityQuery.refetch()}
        resourceLabel="this facility"
      />
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {facilityQuery.data && (
        <header className="border-b-2 border-text-primary pb-4">
          <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
            #02.1 — FACILITY
          </p>
          <h1 className="font-display text-3xl font-bold leading-none text-text-primary sm:text-4xl">
            {facilityQuery.data.name}
          </h1>
          {facilityQuery.data.address && (
            <p className="mt-2 text-sm text-text-muted">{facilityQuery.data.address}</p>
          )}
        </header>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Assets</CardTitle>
          <Button size="sm" onClick={() => setAssetModalOpen(true)}>
            <Plus size={14} strokeWidth={2} />
            Add asset
          </Button>
        </CardHeader>

        {assetsQuery.isError && (
          <QueryErrorState
            error={assetsQuery.error}
            onRetry={() => assetsQuery.refetch()}
            resourceLabel="this facility's assets"
          />
        )}

        {!assetsQuery.isError && assetsQuery.isLoading && <Skeleton className="h-10 w-full" />}

        {!assetsQuery.isError && !assetsQuery.isLoading && assetsQuery.data?.length === 0 && (
          <EmptyState
            icon={Cpu}
            title="No assets yet"
            description="Add one to start monitoring."
            actionLabel="Add asset"
            onAction={() => setAssetModalOpen(true)}
          />
        )}

        {!!assetsQuery.data?.length && (
          <ul className="flex flex-col">
            {assetsQuery.data.map((asset) => (
              <li key={asset.id} className="flex items-center gap-2 border-b border-border py-2 last:border-b-0">
                <Cpu size={14} strokeWidth={1.75} className="text-text-muted" />
                <a
                  href={`/facilities/${facilityId}/assets/${asset.id}`}
                  className="text-sm text-text-primary hover:text-accent-brand-ink"
                >
                  {asset.name}
                </a>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Edge devices</CardTitle>
        </CardHeader>

        {!canManageDevices && (
          <p className="mb-3 text-sm text-text-muted">
            Only admins and operators can register devices and issue ingestion keys.
          </p>
        )}

        {canManageDevices && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              createDevice.mutate();
            }}
            className="mb-4 flex items-end gap-2"
          >
            <div className="flex-1">
              <FormField label="Device name" htmlFor="new-device-name">
                <Input
                  id="new-device-name"
                  placeholder="Roof panel gateway"
                  required
                  value={deviceName}
                  onChange={(e) => setDeviceName(e.target.value)}
                />
              </FormField>
            </div>
            <Button type="submit" size="sm" disabled={createDevice.isPending}>
              {createDevice.isPending ? "Adding…" : "Add device"}
            </Button>
          </form>
        )}

        {devicesQuery.isError && (
          <QueryErrorState
            error={devicesQuery.error}
            onRetry={() => devicesQuery.refetch()}
            resourceLabel="this facility's edge devices"
          />
        )}

        {!devicesQuery.isError && devicesQuery.isLoading && <Skeleton className="h-10 w-full" />}

        {!devicesQuery.isError && !devicesQuery.isLoading && devices.length === 0 && (
          <p className="text-sm text-text-muted">No devices registered yet.</p>
        )}

        {!devicesQuery.isError && !devicesQuery.isLoading && devices.length > 0 && (
          <ul className="flex flex-col">
            {devices.map((device) => (
              <li
                key={device.id}
                className="flex items-center justify-between border-b border-border py-2 last:border-b-0"
              >
                <span className="flex items-center gap-2 text-sm text-text-primary">
                  <Radio size={14} strokeWidth={1.75} className="text-text-muted" />
                  <span className="flex flex-col">
                    {device.name}
                    <span className="text-xs text-text-muted">
                      {device.last_seen_at
                        ? `Last seen ${formatRelativeTime(device.last_seen_at)}`
                        : "Never sent data"}
                    </span>
                  </span>
                </span>
                {canManageDevices && (
                  <div className="flex items-center gap-2">
                    <Button variant="secondary" size="sm" onClick={() => setKeyDialogDeviceId(device.id)}>
                      <KeyRound size={14} strokeWidth={1.75} />
                      Issue key
                    </Button>
                    <Button variant="secondary" size="sm" onClick={() => setCsvUploadDeviceId(device.id)}>
                      <Upload size={14} strokeWidth={1.75} />
                      Upload CSV
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Modal open={assetModalOpen} onClose={() => setAssetModalOpen(false)} title="Add asset">
        {currentOrgId && (
          <AssetForm
            facilityId={facilityId}
            organizationId={currentOrgId}
            onDone={() => {
              setAssetModalOpen(false);
              queryClient.invalidateQueries({ queryKey: qk.assets(facilityId) });
            }}
          />
        )}
      </Modal>

      <IssueKeyDialog
        key={`issue-key-${keyDialogDeviceId ?? "closed"}`}
        open={!!keyDialogDeviceId}
        deviceId={keyDialogDeviceId}
        deviceName={devices.find((d) => d.id === keyDialogDeviceId)?.name ?? ""}
        onClose={() => setKeyDialogDeviceId(null)}
      />

      <CsvUploadDialog
        key={`csv-upload-${csvUploadDeviceId ?? "closed"}`}
        open={!!csvUploadDeviceId}
        onClose={() => setCsvUploadDeviceId(null)}
      />
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/AuthProvider";
import { listAssets, listFacilities } from "@/lib/api/assets";
import { qk } from "@/lib/query/keys";
import { FormField, Select } from "@/components/ui/FormField";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";

export type AssetSelectorValue = {
  facilityId: string | null;
  assetId: string | null;
};

/**
 * Two-step facility -> asset picker. There is no "list all assets across
 * facilities" endpoint, so a facility must be chosen first to scope the
 * asset list. Reusable anywhere a caller needs the user to pick a single
 * asset (copilot, future asset-scoped reports, etc).
 */
export function AssetSelector({
  value,
  onChange,
}: {
  value: AssetSelectorValue;
  onChange: (next: AssetSelectorValue) => void;
}) {
  const { currentOrgId } = useAuth();
  const { facilityId, assetId } = value;

  const facilitiesQuery = useQuery({
    queryKey: qk.facilities(currentOrgId ?? ""),
    queryFn: () => listFacilities(currentOrgId as string),
    enabled: !!currentOrgId,
  });

  const assetsQuery = useQuery({
    queryKey: qk.assets(facilityId ?? ""),
    queryFn: () => listAssets(facilityId as string),
    enabled: !!facilityId,
  });

  if (facilitiesQuery.isError) {
    return (
      <QueryErrorState
        error={facilitiesQuery.error}
        onRetry={() => facilitiesQuery.refetch()}
        resourceLabel="your facilities"
      />
    );
  }

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
      <div className="flex-1">
        <FormField label="Facility" htmlFor="asset-selector-facility">
          {facilitiesQuery.isLoading ? (
            <Skeleton className="h-10 w-full" />
          ) : (
            <Select
              id="asset-selector-facility"
              value={facilityId ?? ""}
              onChange={(e) =>
                onChange({ facilityId: e.target.value || null, assetId: null })
              }
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
      </div>

      <div className="flex-1">
        <FormField label="Asset" htmlFor="asset-selector-asset">
          {!facilityId ? (
            <Select id="asset-selector-asset" value="" disabled>
              <option value="">Select a facility first</option>
            </Select>
          ) : assetsQuery.isLoading ? (
            <Skeleton className="h-10 w-full" />
          ) : assetsQuery.isError ? (
            <Select id="asset-selector-asset" value="" disabled>
              <option value="">Couldn&apos;t load assets — try again</option>
            </Select>
          ) : assetsQuery.data?.length === 0 ? (
            <Select id="asset-selector-asset" value="" disabled>
              <option value="">No assets in this facility</option>
            </Select>
          ) : (
            <Select
              id="asset-selector-asset"
              value={assetId ?? ""}
              onChange={(e) => onChange({ facilityId, assetId: e.target.value || null })}
            >
              <option value="">Select an asset…</option>
              {assetsQuery.data?.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.name}
                </option>
              ))}
            </Select>
          )}
        </FormField>
      </div>
    </div>
  );
}

"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Building2, LayoutGrid } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { listAssets, listAssetTypes, listFacilities } from "@/lib/api/assets";
import { qk } from "@/lib/query/keys";
import { AssetCard } from "@/components/dashboard/AssetCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";

export default function DashboardPage() {
  const router = useRouter();
  const { currentOrgId } = useAuth();

  const facilitiesQuery = useQuery({
    queryKey: qk.facilities(currentOrgId ?? ""),
    queryFn: () => listFacilities(currentOrgId as string),
    enabled: !!currentOrgId,
  });

  const assetTypesQuery = useQuery({ queryKey: qk.assetTypes(), queryFn: listAssetTypes });

  const facilities = facilitiesQuery.data ?? [];
  const assetQueries = useQueries({
    queries: facilities.map((facility) => ({
      queryKey: qk.assets(facility.id),
      queryFn: () => listAssets(facility.id),
      enabled: !!currentOrgId,
    })),
  });

  const assetTypeById = useMemo(() => {
    const map = new Map(assetTypesQuery.data?.map((t) => [t.id, t]));
    return map;
  }, [assetTypesQuery.data]);

  const isLoading =
    facilitiesQuery.isLoading || assetQueries.some((q) => q.isLoading) || assetTypesQuery.isLoading;

  const allAssets = facilities.flatMap((facility, i) =>
    (assetQueries[i]?.data ?? []).map((asset) => ({ asset, facility })),
  );

  return (
    <div className="flex flex-col gap-8">
      <header className="border-b-2 border-text-primary pb-4">
        <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
          #01 — OVERVIEW
        </p>
        <h1 className="font-display text-3xl font-bold leading-none text-text-primary sm:text-4xl">
          Dashboard
        </h1>
      </header>

      {facilitiesQuery.isError && (
        <QueryErrorState
          error={facilitiesQuery.error}
          onRetry={() => facilitiesQuery.refetch()}
          resourceLabel="your facilities"
        />
      )}

      {!facilitiesQuery.isError && isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      )}

      {!facilitiesQuery.isError && !isLoading && facilities.length === 0 && (
        <EmptyState
          icon={Building2}
          title="No facilities yet"
          description="Add a facility to start monitoring its assets."
          actionLabel="Add facility"
          onAction={() => router.push("/facilities")}
        />
      )}

      {!facilitiesQuery.isError && !isLoading && facilities.length > 0 && allAssets.length === 0 && (
        <EmptyState
          icon={LayoutGrid}
          title="No assets yet"
          description="Add one to start monitoring."
          actionLabel="Add asset"
          onAction={() => router.push("/facilities")}
        />
      )}

      {!facilitiesQuery.isError && !isLoading && allAssets.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {allAssets.map(({ asset, facility }, i) => (
            <div
              key={asset.id}
              className="motion-safe:animate-fade-up"
              style={{ animationDelay: `${Math.min(i, 8) * 60}ms` }}
            >
              <AssetCard
                asset={asset}
                assetType={assetTypeById.get(asset.asset_type_id)}
                facilityId={facility.id}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

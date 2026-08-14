"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Building2, Plus } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { listFacilities } from "@/lib/api/assets";
import { qk } from "@/lib/query/keys";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";
import { FacilityForm } from "@/components/facility-admin/FacilityForm";

export default function FacilitiesPage() {
  const { currentOrgId } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);

  const facilitiesQuery = useQuery({
    queryKey: qk.facilities(currentOrgId ?? ""),
    queryFn: () => listFacilities(currentOrgId as string),
    enabled: !!currentOrgId,
  });

  return (
    <div className="flex flex-col gap-8">
      <header className="flex items-end justify-between gap-4 border-b-2 border-text-primary pb-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
            #02 — FACILITIES
          </p>
          <h1 className="font-display text-3xl font-bold leading-none text-text-primary sm:text-4xl">
            Facilities
          </h1>
        </div>
        <Button size="sm" onClick={() => setModalOpen(true)}>
          <Plus size={14} strokeWidth={2} />
          Add facility
        </Button>
      </header>

      {facilitiesQuery.isError && (
        <QueryErrorState
          error={facilitiesQuery.error}
          onRetry={() => facilitiesQuery.refetch()}
          resourceLabel="your facilities"
        />
      )}

      {!facilitiesQuery.isError && facilitiesQuery.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      )}

      {!facilitiesQuery.isError && !facilitiesQuery.isLoading && facilitiesQuery.data?.length === 0 && (
        <EmptyState
          icon={Building2}
          title="No facilities yet"
          description="Add one to start monitoring."
          actionLabel="Add facility"
          onAction={() => setModalOpen(true)}
        />
      )}

      {!facilitiesQuery.isError && !!facilitiesQuery.data?.length && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {facilitiesQuery.data.map((facility) => (
            <Link key={facility.id} href={`/facilities/${facility.id}`} className="group">
              <Card className="h-full transition-shadow hover:shadow-neo-active">
                <div className="flex items-center gap-2">
                  <Building2 size={16} strokeWidth={1.75} className="text-text-muted" />
                  <span className="font-display text-base font-semibold text-text-primary group-hover:text-accent-brand-ink">
                    {facility.name}
                  </span>
                </div>
                {facility.address && (
                  <p className="mt-1 text-sm text-text-muted">{facility.address}</p>
                )}
                <p className="mt-2 font-mono text-xs uppercase tracking-wide text-text-subtle">
                  {facility.timezone}
                </p>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add facility">
        {currentOrgId && (
          <FacilityForm organizationId={currentOrgId} onDone={() => setModalOpen(false)} />
        )}
      </Modal>
    </div>
  );
}

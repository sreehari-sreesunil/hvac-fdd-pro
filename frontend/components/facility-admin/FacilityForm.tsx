"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createFacility } from "@/lib/api/assets";
import { qk } from "@/lib/query/keys";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { FormField, Input } from "@/components/ui/FormField";
import { useToast } from "@/components/ui/Toast";

export function FacilityForm({
  organizationId,
  onDone,
}: {
  organizationId: string;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createFacility({ organization_id: organizationId, name, address: address || undefined });
      await queryClient.invalidateQueries({ queryKey: qk.facilities(organizationId) });
      showToast("Facility added");
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <FormField label="Facility name" htmlFor="new-facility-name">
        <Input id="new-facility-name" required value={name} onChange={(e) => setName(e.target.value)} />
      </FormField>
      <FormField label="Address (optional)" htmlFor="new-facility-address">
        <Input id="new-facility-address" value={address} onChange={(e) => setAddress(e.target.value)} />
      </FormField>
      {error && <p className="text-sm text-accent-critical-ink">{error}</p>}
      <Button type="submit" disabled={submitting} className="self-start">
        {submitting ? "Adding facility…" : "Add facility"}
      </Button>
    </form>
  );
}

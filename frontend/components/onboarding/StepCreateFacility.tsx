"use client";

import { useState } from "react";
import { createFacility } from "@/lib/api/assets";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { FormField, Input } from "@/components/ui/FormField";
import { useToast } from "@/components/ui/Toast";

export function StepCreateFacility({
  organizationId,
  onDone,
}: {
  organizationId: string;
  onDone: (facilityId: string) => void;
}) {
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
      const facility = await createFacility({
        organization_id: organizationId,
        name,
        address: address || undefined,
      });
      showToast("Facility added");
      onDone(facility.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div>
        <h2 className="font-display text-2xl font-bold text-text-primary">
          Add your first facility
        </h2>
        <p className="mt-1 text-sm text-text-muted">A building or site you&apos;ll monitor.</p>
      </div>
      <FormField label="Facility name" htmlFor="facility-name">
        <Input
          id="facility-name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Downtown Distribution Center"
        />
      </FormField>
      <FormField label="Address (optional)" htmlFor="facility-address">
        <Input
          id="facility-address"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="1200 Industrial Way"
        />
      </FormField>
      {error && <p className="text-sm text-accent-critical-ink">{error}</p>}
      <Button type="submit" disabled={submitting} className="self-start">
        {submitting ? "Adding facility…" : "Add facility"}
      </Button>
    </form>
  );
}

"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { FormField, Input } from "@/components/ui/FormField";
import { useToast } from "@/components/ui/Toast";

export function StepCreateOrg({ onDone }: { onDone: () => void }) {
  const { createOrganization } = useAuth();
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createOrganization({ name });
      showToast("Organization added");
      onDone();
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
          Create your organization
        </h2>
        <p className="mt-1 text-sm text-text-muted">
          This groups your facilities, assets, and teammates.
        </p>
      </div>
      <FormField label="Organization name" htmlFor="org-name">
        <Input
          id="org-name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Acme Facilities"
        />
      </FormField>
      {error && <p className="text-sm text-accent-critical-ink">{error}</p>}
      <Button type="submit" disabled={submitting} className="self-start">
        {submitting ? "Adding organization…" : "Add organization"}
      </Button>
    </form>
  );
}

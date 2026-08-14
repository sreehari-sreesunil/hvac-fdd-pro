"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createAsset, createAssetType, listAssetTypes } from "@/lib/api/assets";
import { qk } from "@/lib/query/keys";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { FormField, Input, Select } from "@/components/ui/FormField";
import { useToast } from "@/components/ui/Toast";

const CREATE_NEW = "__create_new__";

export function AssetForm({
  facilityId,
  organizationId,
  onDone,
}: {
  facilityId: string;
  organizationId: string;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const assetTypesQuery = useQuery({
    queryKey: qk.assetTypes(organizationId),
    queryFn: () => listAssetTypes(organizationId),
  });

  const [assetTypeId, setAssetTypeId] = useState("");
  const [newTypeName, setNewTypeName] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const hasTypes = (assetTypesQuery.data?.length ?? 0) > 0;
  // The first real asset type once one has loaded — the fallback the
  // <select> defaults to when the user hasn't explicitly chosen anything.
  // Computed fresh every render (not synced into state via an effect) so
  // it can never drift from what's actually on screen.
  const firstTypeId = assetTypesQuery.data?.[0]?.id ?? null;
  // Previously `assetTypeId || (hasTypes ? "" : CREATE_NEW)`: when
  // untouched, that fell back to "" (matching no real <option>), so the
  // browser silently displayed its own first-option default — an
  // existing type — while `assetTypeId` itself stayed "". Submitting
  // then sent an empty asset_type_id (or, worse, silently discarded a
  // typed "new type name" if the code read `selection` instead).
  // Falling back to the same real id here means the visible selection
  // and the value actually submitted are always the same thing.
  const selection = assetTypeId || firstTypeId || CREATE_NEW;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      let typeId = selection;
      if (selection === CREATE_NEW) {
        const type = await createAssetType({ organization_id: organizationId, name: newTypeName });
        typeId = type.id;
        await queryClient.invalidateQueries({ queryKey: qk.assetTypes(organizationId) });
      }
      await createAsset({ facility_id: facilityId, asset_type_id: typeId, name });
      await queryClient.invalidateQueries({ queryKey: qk.assets(facilityId) });
      showToast("Asset added");
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <FormField label="Asset type" htmlFor="asset-form-type">
        <Select
          id="asset-form-type"
          value={selection}
          onChange={(e) => setAssetTypeId(e.target.value)}
          disabled={assetTypesQuery.isLoading}
        >
          {!hasTypes && <option value={CREATE_NEW}>Create new asset type</option>}
          {assetTypesQuery.data?.map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}
            </option>
          ))}
          {hasTypes && <option value={CREATE_NEW}>+ Create new asset type</option>}
        </Select>
      </FormField>
      {selection === CREATE_NEW && (
        <FormField label="New asset type name" htmlFor="asset-form-new-type">
          <Input
            id="asset-form-new-type"
            required
            value={newTypeName}
            onChange={(e) => setNewTypeName(e.target.value)}
          />
        </FormField>
      )}
      <FormField label="Asset name" htmlFor="asset-form-name">
        <Input id="asset-form-name" required value={name} onChange={(e) => setName(e.target.value)} />
      </FormField>
      {error && <p className="text-sm text-accent-critical-ink">{error}</p>}
      <Button type="submit" disabled={submitting} className="self-start">
        {submitting ? "Adding asset…" : "Add asset"}
      </Button>
    </form>
  );
}

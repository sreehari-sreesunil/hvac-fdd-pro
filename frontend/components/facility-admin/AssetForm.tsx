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

export function AssetForm({ facilityId, onDone }: { facilityId: string; onDone: () => void }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const assetTypesQuery = useQuery({ queryKey: qk.assetTypes(), queryFn: listAssetTypes });

  const [assetTypeId, setAssetTypeId] = useState("");
  const [newTypeName, setNewTypeName] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const hasTypes = (assetTypesQuery.data?.length ?? 0) > 0;
  const selection = assetTypeId || (hasTypes ? "" : CREATE_NEW);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      let typeId = assetTypeId;
      if (selection === CREATE_NEW) {
        const type = await createAssetType({ name: newTypeName });
        typeId = type.id;
        await queryClient.invalidateQueries({ queryKey: qk.assetTypes() });
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

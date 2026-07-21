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

export function StepCreateAsset({
  facilityId,
  onDone,
}: {
  facilityId: string;
  onDone: () => void;
}) {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const assetTypesQuery = useQuery({ queryKey: qk.assetTypes(), queryFn: listAssetTypes });

  const [assetTypeId, setAssetTypeId] = useState<string>("");
  const [newTypeName, setNewTypeName] = useState("");
  const [assetName, setAssetName] = useState("");
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
        const type = await createAssetType({
          name: newTypeName,
          metrics: [
            {
              metric_name: "supply_air_temp",
              display_name: "Supply air temperature",
              unit: "F",
              datatype: "float",
              chart_type: "line",
            },
          ],
        });
        typeId = type.id;
        await queryClient.invalidateQueries({ queryKey: qk.assetTypes() });
      }
      await createAsset({ facility_id: facilityId, asset_type_id: typeId, name: assetName });
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
      <div>
        <h2 className="font-display text-lg font-semibold text-text-primary">
          Add your first asset
        </h2>
        <p className="mt-1 text-sm text-text-muted">
          A unit you&apos;ll monitor, like a rooftop unit or air handler.
        </p>
      </div>

      <FormField label="Asset type" htmlFor="asset-type">
        <Select
          id="asset-type"
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
        <FormField label="New asset type name" htmlFor="new-type-name">
          <Input
            id="new-type-name"
            required
            value={newTypeName}
            onChange={(e) => setNewTypeName(e.target.value)}
            placeholder="Rooftop unit"
          />
        </FormField>
      )}

      <FormField label="Asset name" htmlFor="asset-name">
        <Input
          id="asset-name"
          required
          value={assetName}
          onChange={(e) => setAssetName(e.target.value)}
          placeholder="RTU-3"
        />
      </FormField>

      {error && <p className="text-sm text-accent-critical-ink">{error}</p>}
      <Button type="submit" disabled={submitting} className="self-start">
        {submitting ? "Adding asset…" : "Add asset"}
      </Button>
    </form>
  );
}

"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { uploadTelemetryBulk, uploadTelemetryCsv } from "@/lib/api/telemetry";
import { ApiError } from "@/lib/api-client";
import {
  chunkArray,
  guessTimestampColumn,
  isLongFormatHeader,
  parseCsv,
  pivotWideCsv,
  type ParsedCsv,
} from "@/lib/utils/csv";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { FormField, Input, Select } from "@/components/ui/FormField";
import { AssetSelector, type AssetSelectorValue } from "@/components/shared/AssetSelector";

const BULK_CHUNK_SIZE = 2000;

/**
 * Thrown by the wide-format mutation when a chunk fails partway through the
 * upload — earlier chunks already succeeded server-side, so the failure
 * needs to report what got in, not just that something went wrong.
 */
class PartialUploadError extends Error {
  partial: { accepted: number; unmapped: number; duplicate: number; chunksDone: number; totalChunks: number };

  constructor(
    message: string,
    partial: PartialUploadError["partial"],
  ) {
    super(message);
    this.partial = partial;
  }
}

export function CsvUploadDialog({
  open,
  onClose,
  initialIngestionKey,
}: {
  open: boolean;
  onClose: () => void;
  initialIngestionKey?: string;
}) {
  const [ingestionKey, setIngestionKey] = useState(initialIngestionKey ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [parsed, setParsed] = useState<ParsedCsv | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [timestampColumn, setTimestampColumn] = useState("");
  const [wideAsset, setWideAsset] = useState<AssetSelectorValue>({ facilityId: null, assetId: null });
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);

  const isWide = !!parsed && parsed.headers.length > 0 && !isLongFormatHeader(parsed.headers);

  const mutation = useMutation({
    mutationFn: () => uploadTelemetryCsv(ingestionKey, file as File),
  });

  const wideMutation = useMutation({
    mutationFn: async () => {
      const timestampColumnIndex = parsed!.headers.findIndex((h) => h === timestampColumn);
      const { readings, skipped } = pivotWideCsv(parsed!, timestampColumnIndex, wideAsset.assetId as string);
      const chunks = chunkArray(readings, BULK_CHUNK_SIZE);

      let accepted = 0;
      let unmapped = 0;
      let duplicate = 0;
      setProgress({ done: 0, total: chunks.length || 1 });

      for (let i = 0; i < chunks.length; i++) {
        try {
          const res = await uploadTelemetryBulk(ingestionKey, chunks[i]);
          accepted += res.accepted_count;
          unmapped += res.unmapped_count;
          duplicate += res.duplicate_count;
          setProgress({ done: i + 1, total: chunks.length });
        } catch (err) {
          const message = err instanceof ApiError ? err.message : "Couldn't reach the telemetry service.";
          throw new PartialUploadError(message, {
            accepted,
            unmapped,
            duplicate,
            chunksDone: i,
            totalChunks: chunks.length,
          });
        }
      }

      return { accepted_count: accepted, unmapped_count: unmapped, duplicate_count: duplicate, skipped };
    },
  });

  async function onFileChange(f: File | null) {
    setFile(f);
    setParsed(null);
    setParseError(null);
    setProgress(null);
    mutation.reset();
    wideMutation.reset();
    if (!f) return;

    try {
      const text = await f.text();
      const result = parseCsv(text);
      setParsed(result);
      if (!isLongFormatHeader(result.headers)) {
        setTimestampColumn(guessTimestampColumn(result.headers) ?? "");
      }
    } catch {
      setParseError("Couldn't read this file as CSV.");
    }
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ingestionKey || !file || !parsed) return;
    if (isWide) {
      if (!timestampColumn || !wideAsset.assetId || wideMutation.isPending) return;
      wideMutation.mutate();
    } else {
      if (mutation.isPending) return;
      mutation.mutate();
    }
  }

  const result = mutation.data;
  const errorMessage = !isWide
    ? mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.isError
        ? "Couldn't reach the telemetry service."
        : null
    : wideMutation.error instanceof PartialUploadError
      ? wideMutation.error.message
      : wideMutation.error instanceof ApiError
        ? wideMutation.error.message
        : wideMutation.isError
          ? "Couldn't reach the telemetry service."
          : null;

  const partialInfo =
    isWide && wideMutation.error instanceof PartialUploadError && wideMutation.error.partial.chunksDone > 0
      ? wideMutation.error.partial
      : null;

  const summaryParts = result
    ? [
        `${result.accepted_count.toLocaleString()} readings ingested`,
        result.duplicate_count > 0 ? `${result.duplicate_count.toLocaleString()} duplicates skipped` : null,
        result.unmapped_count > 0 ? `${result.unmapped_count.toLocaleString()} unmapped metrics` : null,
      ].filter(Boolean)
    : [];

  const wideResult = wideMutation.data;
  const wideSummaryParts = wideResult
    ? [
        `${wideResult.accepted_count.toLocaleString()} readings ingested`,
        wideResult.duplicate_count > 0
          ? `${wideResult.duplicate_count.toLocaleString()} duplicates skipped`
          : null,
        wideResult.unmapped_count > 0
          ? `${wideResult.unmapped_count.toLocaleString()} unmapped metrics`
          : null,
      ].filter(Boolean)
    : [];

  const isPending = isWide ? wideMutation.isPending : mutation.isPending;
  const submitDisabled =
    !ingestionKey ||
    !file ||
    !parsed ||
    (isWide ? !timestampColumn || !wideAsset.assetId || isPending : isPending);
  const hasResult = isWide ? !!wideResult : !!result;

  return (
    <Modal open={open} onClose={onClose} title="Upload telemetry CSV" className="max-w-lg">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <FormField label="Ingestion key" htmlFor="csv-upload-key">
          <Input
            id="csv-upload-key"
            placeholder="Paste the device's ingestion key"
            value={ingestionKey}
            onChange={(e) => setIngestionKey(e.target.value)}
            required
          />
        </FormField>

        <FormField label="CSV file" htmlFor="csv-upload-file">
          <input
            id="csv-upload-file"
            type="file"
            accept=".csv"
            onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
            className="text-sm text-text-primary file:mr-3 file:rounded-md file:border file:border-border file:bg-elevated file:px-3 file:py-1.5 file:text-sm file:text-text-primary"
            required
          />
        </FormField>

        {parseError && <p className="text-sm text-accent-critical-ink">{parseError}</p>}

        {!isWide && (
          <p className="text-xs text-text-muted">
            Expected columns: asset_id, external_key, value, recorded_at (idempotency_key
            optional). Column names are matched case-insensitively.
          </p>
        )}

        {isWide && parsed && (
          <div className="flex flex-col gap-3 rounded-md border border-border bg-elevated p-3">
            <p className="text-xs text-text-muted">
              Detected wide format — each other column becomes a metric for the asset you
              choose below. Select which column is the timestamp and which asset these
              readings belong to.
            </p>

            <FormField label="Timestamp column" htmlFor="csv-upload-timestamp-column">
              <Select
                id="csv-upload-timestamp-column"
                value={timestampColumn}
                onChange={(e) => setTimestampColumn(e.target.value)}
              >
                <option value="">Select the timestamp column…</option>
                {parsed.headers.map((header) => (
                  <option key={header} value={header}>
                    {header}
                  </option>
                ))}
              </Select>
            </FormField>

            <AssetSelector value={wideAsset} onChange={setWideAsset} />
          </div>
        )}

        {errorMessage && <p className="text-sm text-accent-critical-ink">{errorMessage}</p>}

        {partialInfo && (
          <p className="text-xs text-text-muted">
            {`${partialInfo.accepted.toLocaleString()} readings were ingested from batch ${partialInfo.chunksDone} of ${partialInfo.totalChunks} before this error.`}
          </p>
        )}

        {!isWide && result && (
          <div className="flex flex-col gap-2 rounded-md border border-border bg-elevated p-3">
            <p className="text-sm text-text-primary">{summaryParts.join(", ")}.</p>

            {result.unmapped_count > 0 && (
              <p className="text-xs text-text-muted">
                {`${result.unmapped_count.toLocaleString()} metric key${result.unmapped_count === 1 ? "" : "s"} weren't recognized for their assets. Map them from each asset's detail page.`}
              </p>
            )}

            {result.invalid_rows.length > 0 && (
              <ul className="max-h-48 overflow-y-auto text-xs text-accent-critical-ink">
                {result.invalid_rows.map((rowError, i) => (
                  <li key={i} className="border-b border-border/50 py-1 last:border-b-0">
                    {rowError.row === 0 ? "File" : `Row ${rowError.row}`}: {rowError.error}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {isWide && wideResult && (
          <div className="flex flex-col gap-2 rounded-md border border-border bg-elevated p-3">
            <p className="text-sm text-text-primary">{wideSummaryParts.join(", ")}.</p>

            {wideResult.unmapped_count > 0 && (
              <p className="text-xs text-text-muted">
                {`${wideResult.unmapped_count.toLocaleString()} metric key${wideResult.unmapped_count === 1 ? "" : "s"} weren't recognized for their assets. Map them from each asset's detail page.`}
              </p>
            )}

            {wideResult.skipped.length > 0 && (
              <>
                <p className="text-xs text-text-muted">
                  {`${wideResult.skipped.length.toLocaleString()} cell${wideResult.skipped.length === 1 ? "" : "s"} skipped:`}
                </p>
                <ul className="max-h-48 overflow-y-auto text-xs text-accent-critical-ink">
                  {wideResult.skipped.map((cell, i) => (
                    <li key={i} className="border-b border-border/50 py-1 last:border-b-0">
                      Row {cell.row}, {cell.column}: {cell.reason}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>
            {hasResult ? "Close" : "Cancel"}
          </Button>
          <Button type="submit" size="sm" disabled={submitDisabled}>
            {isPending
              ? isWide && progress
                ? `Uploading batch ${progress.done}/${progress.total}…`
                : "Uploading…"
              : "Upload"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

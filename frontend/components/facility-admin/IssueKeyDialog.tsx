"use client";

import { useEffect, useState } from "react";
import { Copy, Check, AlertTriangle } from "lucide-react";
import { issueIngestionKey } from "@/lib/api/telemetry";
import { ApiError } from "@/lib/api-client";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { CsvUploadDialog } from "./CsvUploadDialog";

export function IssueKeyDialog({
  open,
  deviceId,
  deviceName,
  onClose,
}: {
  open: boolean;
  deviceId: string | null;
  deviceName: string;
  onClose: () => void;
}) {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [copied, setCopied] = useState(false);
  const [csvDialogOpen, setCsvDialogOpen] = useState(false);

  // The parent remounts this component (via a `key` on deviceId) whenever a
  // different device's dialog opens, so local state starts fresh without
  // needing to reset it here.
  useEffect(() => {
    if (!open || !deviceId) return;
    issueIngestionKey(deviceId)
      .then((res) => setApiKey(res.api_key))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't issue a key."));
  }, [open, deviceId]);

  function handleClose() {
    if (apiKey && !acknowledged) return;
    onClose();
  }

  return (
    <Modal open={open} onClose={handleClose} title={`Ingestion key for ${deviceName}`}>
      {error && <p className="text-sm text-accent-critical-ink">{error}</p>}

      {!error && !apiKey && <p className="text-sm text-text-muted">Issuing key…</p>}

      {apiKey && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 rounded-md border border-accent-warning/30 bg-accent-warning/10 p-3 text-sm text-accent-warning-ink">
            <AlertTriangle size={16} strokeWidth={1.75} className="mt-0.5 shrink-0" />
            <span>This key won&apos;t be shown again. Copy it now.</span>
          </div>

          <div className="flex items-center gap-2 rounded-md border border-border bg-bg p-3">
            <code className="flex-1 overflow-x-auto font-mono-num text-sm text-text-primary">
              {apiKey}
            </code>
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(apiKey);
                setCopied(true);
              }}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text-muted hover:bg-elevated hover:text-text-primary"
              aria-label="Copy key"
            >
              {copied ? (
                <Check size={16} strokeWidth={1.75} className="text-accent-primary-ink" />
              ) : (
                <Copy size={16} strokeWidth={1.75} />
              )}
            </button>
          </div>

          <label className="flex items-start gap-2 text-sm text-text-primary">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="mt-0.5"
            />
            I&apos;ve copied this key and understand it won&apos;t be shown again.
          </label>

          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => setCsvDialogOpen(true)}
              disabled={!acknowledged}
            >
              Upload CSV now
            </Button>
            <Button onClick={handleClose} disabled={!acknowledged}>
              Done
            </Button>
          </div>
        </div>
      )}

      {apiKey && (
        <CsvUploadDialog
          key={csvDialogOpen ? "open" : "closed"}
          open={csvDialogOpen}
          onClose={() => setCsvDialogOpen(false)}
          initialIngestionKey={apiKey}
        />
      )}
    </Modal>
  );
}

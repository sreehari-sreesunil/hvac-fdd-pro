import { SearchX } from "lucide-react";

/** Calm, explicitly not styled as an error. */
export function InsufficientEvidenceState() {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-border bg-elevated p-4 text-sm text-text-muted">
      <SearchX size={16} strokeWidth={1.75} className="mt-0.5 shrink-0" />
      <p>
        There isn&apos;t enough recent telemetry to support a diagnosis here. Try asking again once
        more readings come in.
      </p>
    </div>
  );
}

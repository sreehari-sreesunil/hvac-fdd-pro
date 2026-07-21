import { FileText, Radio } from "lucide-react";
import { MonoValue } from "@/components/ui/MonoValue";

// MOCK: static preview content, not a live copilot session — no copilot
// backend exists yet. See lib/mock-copilot.ts for the real chat mock data.
export function CopilotPreview() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-20">
      <h2 className="font-display text-2xl font-semibold text-text-primary">
        Ask it what&apos;s wrong, get the evidence back
      </h2>
      <p className="mt-2 text-sm text-text-muted">
        A preview of how the copilot will answer once it&apos;s connected to a model.
      </p>

      <div className="mt-8 rounded-xl border border-border bg-surface p-6">
        <p className="text-sm text-text-muted">
          Why is RTU-3 running hotter than usual today?
        </p>
        <div className="mt-4 rounded-lg border border-border bg-elevated p-4">
          <p className="text-sm text-text-primary">
            RTU-3&apos;s suction-line superheat has drifted 14°F over the last 6 hours, consistent
            with early-stage refrigerant undercharge.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1 rounded-full border border-border bg-surface px-2.5 py-1 text-xs text-text-muted">
              <Radio size={12} strokeWidth={1.75} />
              RTU-3 · suction temp
            </span>
            <span className="inline-flex items-center gap-1 rounded-full border border-border bg-surface px-2.5 py-1 text-xs text-text-muted">
              <FileText size={12} strokeWidth={1.75} />
              Fault code R-410A-12
            </span>
          </div>
          <p className="mt-3 text-xs text-text-muted">
            Confidence{" "}
            <MonoValue className="text-text-primary">82%</MonoValue>
          </p>
        </div>
      </div>
    </section>
  );
}

import { MOCK_EVAL_METRICS } from "@/lib/mock-copilot";
import { MonoValue } from "@/components/ui/MonoValue";

const ROWS = [
  { label: "Precision", value: MOCK_EVAL_METRICS.precision },
  { label: "Recall", value: MOCK_EVAL_METRICS.recall },
  { label: "F1 score", value: MOCK_EVAL_METRICS.f1 },
];

export function EvalMetricsSection() {
  return (
    <section className="mx-auto max-w-4xl px-4 py-20">
      <h2 className="font-display text-2xl font-semibold text-text-primary">
        Evaluated across a dozen fault classes
      </h2>
      {/* MOCK: illustrative numbers — no fault-detection model exists yet. */}
      <p className="mt-2 text-sm text-text-muted">
        Illustrative figures for a future fault-detection model. Not measured against live data.
      </p>
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {ROWS.map((row) => (
          <div key={row.label} className="rounded-xl border border-border bg-surface p-6">
            <MonoValue className="block text-3xl font-semibold text-accent-primary" as="div">
              {(row.value * 100).toFixed(0)}%
            </MonoValue>
            <p className="mt-1 text-sm text-text-muted">{row.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

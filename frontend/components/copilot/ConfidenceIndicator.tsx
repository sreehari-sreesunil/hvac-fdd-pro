import { MonoValue } from "@/components/ui/MonoValue";

/** Same mono-numeral treatment as real sensor data, despite being mock. */
export function ConfidenceIndicator({ confidence }: { confidence: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-text-muted">
      Confidence
      <MonoValue className="text-text-primary">{Math.round(confidence * 100)}%</MonoValue>
    </span>
  );
}

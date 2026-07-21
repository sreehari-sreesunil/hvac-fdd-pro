import { DISCONNECTED_THRESHOLD_MS, STALE_THRESHOLD_MS } from "./constants";

export type Reliability = "live" | "stale" | "disconnected";

/**
 * Pure, metadata-driven state derivation from the age of the most recent
 * telemetry reading. Never hardcoded to a specific asset.
 */
export function deriveReliability(
  lastRecordedAt: string | null,
  now: number = Date.now(),
): Reliability {
  if (!lastRecordedAt) return "disconnected";
  const age = now - new Date(lastRecordedAt).getTime();
  if (age < STALE_THRESHOLD_MS) return "live";
  if (age < DISCONNECTED_THRESHOLD_MS) return "stale";
  return "disconnected";
}

/** Dev-only override so QA can see the disconnected state without starving the pipeline. */
export function applySimulatedReliability(
  actual: Reliability,
  searchParams: URLSearchParams | null,
): Reliability {
  if (process.env.NODE_ENV === "production" || !searchParams) return actual;
  const sim = searchParams.get("simulateReliability");
  if (sim === "live" || sim === "stale" || sim === "disconnected") return sim;
  return actual;
}

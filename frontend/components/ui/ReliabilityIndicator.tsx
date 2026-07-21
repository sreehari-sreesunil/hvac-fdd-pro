"use client";

import { Clock, PlugZap } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { formatRelativeTime } from "@/lib/utils/format";
import type { Reliability } from "@/lib/reliability/deriveReliability";

/**
 * Renders one of the three explicit reliability states. Color is never the
 * sole signal — each state pairs a distinct icon shape with its color.
 */
export function ReliabilityIndicator({
  state,
  lastRecordedAt,
  className,
}: {
  state: Reliability;
  lastRecordedAt: string | null;
  className?: string;
}) {
  if (state === "live") {
    return (
      <div className={cn("flex items-center gap-1.5 text-accent-primary-ink", className)}>
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full rounded-full bg-accent-primary motion-safe:animate-pulse-live" />
        </span>
        <span className="text-xs font-medium">Live</span>
      </div>
    );
  }

  if (state === "stale") {
    return (
      <div className={cn("flex items-center gap-1.5 text-accent-warning-ink", className)}>
        <Clock size={14} strokeWidth={1.75} aria-hidden />
        <span className="text-xs font-medium">
          Stale
          {lastRecordedAt && (
            <>
              {" "}
              <span className="font-mono-num text-text-muted">
                &middot; last updated {formatRelativeTime(lastRecordedAt)}
              </span>
            </>
          )}
        </span>
      </div>
    );
  }

  // Disconnected — calm, explicitly not styled as an error.
  return (
    <div className={cn("flex items-center gap-1.5 text-text-muted", className)}>
      <PlugZap size={14} strokeWidth={1.75} aria-hidden />
      <span className="text-xs font-medium">Awaiting localized heartbeat</span>
    </div>
  );
}

/** Small dot-only variant for tight spaces like sidebar tree rows. */
export function ReliabilityDot({ state }: { state: Reliability }) {
  const toneClass =
    state === "live"
      ? "bg-accent-primary"
      : state === "stale"
        ? "bg-accent-warning"
        : "bg-text-muted";
  return (
    <span className="inline-flex items-center" title={state}>
      <span className={cn("h-1.5 w-1.5 rounded-full", toneClass)} />
      <span className="sr-only">{state}</span>
    </span>
  );
}

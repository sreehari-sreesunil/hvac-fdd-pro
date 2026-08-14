"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

/**
 * The real backend runs an agentic tool-calling loop (up to 5 iterations)
 * before it has anything to say, so a static spinner reads as broken for
 * several seconds. These phrases are genuinely generic — not fabricated
 * tool names, since which tools actually run isn't known until the
 * response comes back (that's what the tools_called footer is for).
 */
const THINKING_PHRASES = [
  "Reasoning about the question…",
  "Checking telemetry and documentation…",
  "Weighing the evidence…",
];

export function ThinkingIndicator() {
  const [phraseIndex, setPhraseIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setPhraseIndex((i) => (i + 1) % THINKING_PHRASES.length);
    }, 1800);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex justify-start motion-safe:animate-fade-up">
      <div className="flex max-w-lg items-center gap-3 rounded-surface border-l-2 border-accent-glow bg-neo-base p-4 shadow-neo-resting">
        <Sparkles
          size={16}
          strokeWidth={1.75}
          className="shrink-0 text-accent-glow-ink shadow-[0_0_6px_var(--accent-glow)]"
        />
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-accent-glow motion-safe:animate-pulse-live" />
          <span
            className="h-1.5 w-1.5 rounded-full bg-accent-glow motion-safe:animate-pulse-live"
            style={{ animationDelay: "0.2s" }}
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-accent-glow motion-safe:animate-pulse-live"
            style={{ animationDelay: "0.4s" }}
          />
        </div>
        <span className="font-mono text-xs text-text-muted">
          {THINKING_PHRASES[phraseIndex]}
        </span>
      </div>
    </div>
  );
}

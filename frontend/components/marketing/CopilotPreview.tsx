"use client";

import { motion } from "framer-motion";
import { FileText, Radio } from "lucide-react";
import { MonoValue } from "@/components/ui/MonoValue";
import { Badge } from "@/components/ui/Badge";
import { usePrefersReducedMotion } from "@/lib/utils/usePrefersReducedMotion";

// MOCK: static preview content, not a live copilot session — no copilot
// backend exists yet. See lib/mock-copilot.ts for the real chat mock data.
export function CopilotPreview() {
  const reduceMotion = usePrefersReducedMotion();

  return (
    <section className="mx-auto max-w-3xl px-4 py-20">
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
          #02 — AI COPILOT
        </p>
        <h2 className="font-display text-3xl font-bold text-text-primary sm:text-4xl">
          Ask it what&apos;s wrong, get the evidence back
        </h2>
        <p className="mt-2 text-sm text-text-muted">
          A preview of how the copilot will answer once it&apos;s connected to a model.
        </p>
      </motion.div>

      <motion.div
        className="mt-8 rounded-surface bg-elevated p-6 shadow-neo-resting"
        initial={reduceMotion ? false : { opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.4, ease: "easeOut", delay: 0.1 }}
      >
        <p className="text-sm text-text-muted">
          Why is RTU-3 running hotter than usual today?
        </p>
        <div className="mt-4 rounded-surface bg-neo-base p-4 shadow-[0_0_0_1px_var(--accent-glow)_inset]">
          <p className="text-sm text-text-primary">
            RTU-3&apos;s suction-line superheat has drifted 14°F over the last 6 hours, consistent
            with early-stage refrigerant undercharge.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge tone="glow" icon={Radio}>
              RTU-3 · suction temp
            </Badge>
            <Badge tone="glow" icon={FileText}>
              Fault code R-410A-12
            </Badge>
          </div>
          <p className="mt-3 text-xs text-text-muted">
            Confidence{" "}
            <MonoValue className="text-accent-glow-ink">82%</MonoValue>
          </p>
        </div>
      </motion.div>
    </section>
  );
}

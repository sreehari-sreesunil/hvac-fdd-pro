"use client";

import { motion } from "framer-motion";
import { MOCK_EVAL_METRICS } from "@/lib/mock-copilot";
import { MonoValue } from "@/components/ui/MonoValue";
import { usePrefersReducedMotion } from "@/lib/utils/usePrefersReducedMotion";

const ROWS = [
  { label: "Precision", value: MOCK_EVAL_METRICS.precision },
  { label: "Recall", value: MOCK_EVAL_METRICS.recall },
  { label: "F1 score", value: MOCK_EVAL_METRICS.f1 },
];

export function EvalMetricsSection() {
  const reduceMotion = usePrefersReducedMotion();

  return (
    <section className="mx-auto max-w-4xl px-4 py-20">
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
          #01 — MODEL EVALUATION
        </p>
        <h2 className="font-display text-3xl font-bold text-text-primary sm:text-4xl">
          Evaluated across a dozen fault classes
        </h2>
        {/* MOCK: illustrative numbers — no fault-detection model exists yet. */}
        <p className="mt-2 text-sm text-text-muted">
          Illustrative figures for a future fault-detection model. Not measured against live data.
        </p>
      </motion.div>
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {ROWS.map((row, i) => (
          <motion.div
            key={row.label}
            className="rounded-surface bg-neo-base p-6 shadow-neo-resting"
            initial={reduceMotion ? false : { opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.4, ease: "easeOut", delay: i * 0.08 }}
          >
            <MonoValue className="block text-3xl font-semibold text-accent-brand-ink" as="div">
              {(row.value * 100).toFixed(0)}%
            </MonoValue>
            <p className="mt-1 text-sm text-text-muted">{row.label}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

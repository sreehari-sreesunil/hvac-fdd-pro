"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/Button";
import { usePrefersReducedMotion } from "@/lib/utils/usePrefersReducedMotion";

export function CTASection() {
  const reduceMotion = usePrefersReducedMotion();

  return (
    <section className="mx-auto max-w-2xl px-4 py-24 text-center">
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        <h2 className="font-display text-3xl font-bold text-text-primary sm:text-4xl">
          Start monitoring your fleet
        </h2>
        <p className="mt-2 text-sm text-text-muted">
          Connect your facilities and assets in a few steps.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/signup">
            <Button>Sign up</Button>
          </Link>
          <Link href="/login">
            <Button variant="secondary">Log in</Button>
          </Link>
        </div>
      </motion.div>
    </section>
  );
}

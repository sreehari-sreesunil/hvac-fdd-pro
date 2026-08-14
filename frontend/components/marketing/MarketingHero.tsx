"use client";

import { useRef } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform } from "framer-motion";
import { Button } from "@/components/ui/Button";
import { HeroSchematic } from "@/components/marketing/HeroSchematic";
import { usePrefersReducedMotion } from "@/lib/utils/usePrefersReducedMotion";

/**
 * The hero pins for a stretch of scroll while the schematic scrubs in a
 * "diagnostic reveal" — the compressor zooms in slightly and the fault
 * callout fades on, as if the system is homing in on the anomaly as the
 * visitor scrolls. Reserved for this page only: a public, low-frequency,
 * first-impression surface is exactly where a pinned moment earns its
 * place per the motion system's own guidance — nothing else in the app
 * pins on scroll.
 */
export function MarketingHero() {
  const reduceMotion = usePrefersReducedMotion();
  const sectionRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end end"],
  });

  const schematicScale = useTransform(scrollYProgress, [0, 1], [1, 1.12]);
  const faultOpacity = useTransform(scrollYProgress, [0.25, 0.55], [0, 1]);
  const headlineY = useTransform(scrollYProgress, [0, 1], [0, -48]);
  const contentOpacity = useTransform(scrollYProgress, [0.7, 1], [1, 0.35]);

  const content = (
    <>
      <motion.div className="flex-1" style={reduceMotion ? undefined : { y: headlineY }}>
        <h1 className="font-display text-4xl font-bold leading-[0.95] text-text-primary sm:text-5xl lg:text-6xl">
          Catch HVAC faults before they cost you a service call.
        </h1>
        <p className="mt-5 max-w-md text-base text-text-muted">
          Live telemetry, fleet-wide visibility, and an AI copilot that explains what&apos;s wrong
          and why — for commercial rooftop units, air handlers, and chillers.
        </p>
        <div className="mt-8 flex gap-3">
          <Link href="/signup">
            <Button>Sign up</Button>
          </Link>
          <Link href="/login">
            <Button variant="secondary">Log in</Button>
          </Link>
        </div>
      </motion.div>
      <motion.div
        className="h-64 w-full flex-1 sm:h-80 lg:h-96"
        style={reduceMotion ? undefined : { scale: schematicScale }}
      >
        <HeroSchematic faultOpacity={reduceMotion ? 1 : faultOpacity} />
      </motion.div>
    </>
  );

  if (reduceMotion) {
    return (
      <section className="relative mx-auto flex max-w-6xl flex-col-reverse items-center gap-10 overflow-hidden px-4 py-16 lg:flex-row lg:py-24">
        {content}
      </section>
    );
  }

  return (
    <section ref={sectionRef} className="relative h-[220vh]">
      <motion.div
        className="sticky top-0 mx-auto flex h-screen max-w-6xl flex-col-reverse items-center justify-center gap-10 overflow-hidden px-4 lg:flex-row"
        style={{ opacity: contentOpacity }}
      >
        {content}
      </motion.div>
    </section>
  );
}

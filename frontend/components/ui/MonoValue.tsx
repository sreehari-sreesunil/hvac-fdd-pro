"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils/cn";

/**
 * Tabular-numeral display for sensor readings, timestamps, confidence
 * scores, fault codes, and IDs. Units are always shown explicitly by the
 * caller as part of `children` (e.g. "71.2°F"), never a bare number.
 * Re-renders trigger a brief roll/tick transition instead of an instant
 * swap, gated by prefers-reduced-motion via motion-safe:.
 */
export function MonoValue({
  children,
  className,
  as: Tag = "span",
}: {
  children: React.ReactNode;
  className?: string;
  as?: "span" | "div";
}) {
  const [tick, setTick] = useState(0);
  const prevValue = useRef(children);

  useEffect(() => {
    if (prevValue.current !== children) {
      prevValue.current = children;
      setTick((t) => t + 1);
    }
  }, [children]);

  return (
    <Tag
      key={tick}
      className={cn("font-mono-num motion-safe:animate-roll-tick", className)}
    >
      {children}
    </Tag>
  );
}

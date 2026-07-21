"use client";

import { useEffect, useState } from "react";

// Decorative animated schematic — the numbers below are illustrative motion,
// not real telemetry (the marketing page has no data connection).
export function HeroSchematic() {
  const [supplyTemp, setSupplyTemp] = useState(58.4);
  // SMIL <animateMotion> doesn't respond to the motion-safe: CSS variant, so
  // the traveling flow dots are only rendered when motion is allowed.
  const [reduceMotion, setReduceMotion] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    const id = setInterval(() => {
      setSupplyTemp((prev) => Math.round((prev + (Math.random() - 0.5) * 0.6) * 10) / 10);
    }, 2500);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  return (
    <svg
      viewBox="0 0 800 520"
      className="h-full w-full text-accent-primary"
      role="img"
      aria-label="Schematic of a rooftop HVAC unit with supply air, return air, compressor, and coils"
    >
      <g fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.6">
        <rect x="140" y="90" width="520" height="240" rx="10" />
        <line x1="140" y1="170" x2="660" y2="170" />
        <line x1="140" y1="250" x2="660" y2="250" />
        <line x1="300" y1="90" x2="300" y2="330" />
        <line x1="500" y1="90" x2="500" y2="330" />
      </g>

      {/* Compressor */}
      <circle cx="220" cy="210" r="34" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.7" />
      <circle cx="220" cy="210" r="18" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.7" />

      {/* Coils */}
      <g fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.7">
        <path d="M 370 130 q 20 20 0 40 q -20 20 0 40 q 20 20 0 40" />
        <path d="M 420 130 q 20 20 0 40 q -20 20 0 40 q 20 20 0 40" />
      </g>

      {/* Supply / return air ducts with traveling flow dots */}
      <path
        id="supplyPath"
        d="M 660 210 C 730 210, 760 160, 760 100"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.5"
      />
      <path
        id="returnPath"
        d="M 140 210 C 70 210, 40 260, 40 320"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        opacity="0.5"
      />

      {!reduceMotion && (
        <g>
          <circle r="3" fill="currentColor">
            <animateMotion dur="3.2s" repeatCount="indefinite">
              <mpath href="#supplyPath" />
            </animateMotion>
          </circle>
          <circle r="3" fill="currentColor">
            <animateMotion dur="4s" repeatCount="indefinite" begin="1s">
              <mpath href="#returnPath" />
            </animateMotion>
          </circle>
        </g>
      )}

      {/* Live-updating sensor point */}
      <g transform="translate(560, 260)">
        <circle r="5" fill="currentColor" className="motion-safe:animate-pulse-live" />
        <text x="12" y="4" className="font-mono-num" fontSize="13" fill="currentColor">
          {supplyTemp.toFixed(1)}°F
        </text>
      </g>

      {/* Mid-fault sensor point with annotation callout */}
      <g transform="translate(240, 300)" className="text-accent-warning">
        <circle r="5" fill="currentColor" className="motion-safe:animate-pulse-live" />
        <line x1="0" y1="0" x2="30" y2="-40" stroke="currentColor" strokeWidth="1" opacity="0.6" />
        <text x="34" y="-40" fontSize="12" fill="currentColor" className="font-sans">
          Superheat drift detected
        </text>
      </g>
    </svg>
  );
}

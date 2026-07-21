/** Subtle schematic linework motif used as a background motif (not a decorative illustration). */
export function SchematicBackground({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 800 600"
      className={className}
      aria-hidden
      preserveAspectRatio="xMidYMid slice"
    >
      <g fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5">
        <rect x="120" y="80" width="560" height="280" rx="8" />
        <line x1="120" y1="180" x2="680" y2="180" />
        <line x1="120" y1="280" x2="680" y2="280" />
        <line x1="260" y1="80" x2="260" y2="360" />
        <line x1="420" y1="80" x2="420" y2="360" />
        <line x1="560" y1="80" x2="560" y2="360" />
        <circle cx="340" cy="230" r="36" />
        <circle cx="340" cy="230" r="20" />
        <path d="M 120 440 C 260 400, 540 480, 680 440" />
        <path d="M 120 500 C 260 460, 540 540, 680 500" />
      </g>
    </svg>
  );
}

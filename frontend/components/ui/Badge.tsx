import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils/cn";

type Tone = "neutral" | "primary" | "warning" | "critical" | "glow";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-neo-base text-text-muted",
  primary: "bg-accent-brand/10 text-accent-brand-ink",
  warning: "bg-accent-warning/10 text-accent-warning-ink",
  critical: "bg-accent-critical/10 text-accent-critical-ink",
  /** Reserved for AI/predictive surfaces (Copilot, fault attribution) —
   *  never a general-purpose accent. */
  glow: "bg-accent-glow/10 text-accent-glow-ink",
};

export function Badge({
  tone = "neutral",
  icon: Icon,
  children,
  className,
}: {
  tone?: Tone;
  icon?: LucideIcon;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-surface px-2.5 py-1 font-mono text-xs font-medium uppercase tracking-wide shadow-neo-resting",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {Icon && <Icon size={12} strokeWidth={2} aria-hidden />}
      {children}
    </span>
  );
}

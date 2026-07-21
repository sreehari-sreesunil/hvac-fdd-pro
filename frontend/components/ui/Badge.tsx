import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils/cn";

type Tone = "neutral" | "primary" | "warning" | "critical";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-elevated text-text-muted border-border",
  primary: "bg-accent-primary/10 text-accent-primary-ink border-accent-primary/30",
  warning: "bg-accent-warning/10 text-accent-warning-ink border-accent-warning/30",
  critical: "bg-accent-critical/10 text-accent-critical-ink border-accent-critical/30",
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
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {Icon && <Icon size={12} strokeWidth={2} aria-hidden />}
      {children}
    </span>
  );
}

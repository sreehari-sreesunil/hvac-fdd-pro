import type { LucideIcon } from "lucide-react";
import { Button } from "./Button";

/** Empty states read as instructions, not apologies — no illustrations. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border py-16 text-center">
      <Icon size={28} strokeWidth={1.5} className="text-text-muted" aria-hidden />
      <div className="flex flex-col gap-1">
        <p className="font-display text-base font-semibold text-text-primary">{title}</p>
        <p className="max-w-sm text-sm text-text-muted">{description}</p>
      </div>
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction} className="mt-2">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

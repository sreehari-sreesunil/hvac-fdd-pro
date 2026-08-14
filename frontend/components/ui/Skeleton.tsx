import { cn } from "@/lib/utils/cn";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-surface bg-neo-base opacity-70 motion-safe:animate-pulse", className)} />
  );
}

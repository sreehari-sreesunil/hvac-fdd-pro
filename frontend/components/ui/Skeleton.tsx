import { cn } from "@/lib/utils/cn";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-md bg-elevated opacity-70 motion-safe:animate-pulse", className)} />
  );
}

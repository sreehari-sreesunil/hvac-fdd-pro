/** Formats a duration since `isoDate` as compact mono text, e.g. "42s ago", "3m ago", "2h ago". */
export function formatRelativeTime(isoDate: string, now: number = Date.now()): string {
  const then = new Date(isoDate).getTime();
  const diffMs = Math.max(0, now - then);
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function formatTimestamp(isoDate: string): string {
  return new Date(isoDate).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

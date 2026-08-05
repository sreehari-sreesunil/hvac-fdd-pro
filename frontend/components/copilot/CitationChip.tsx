import { BookOpen } from "lucide-react";

/** `source` is a raw sources_used entry, e.g. "lbnl_fdd_review.txt::3". */
export function CitationChip({ source }: { source: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-elevated px-2.5 py-1 text-xs text-text-muted">
      <BookOpen size={12} strokeWidth={1.75} />
      {source}
    </span>
  );
}

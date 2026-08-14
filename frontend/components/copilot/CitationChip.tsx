import { BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

/** `source` is a raw sources_used entry, e.g. "lbnl_fdd_review.txt::3". */
export function CitationChip({ source }: { source: string }) {
  return (
    <Badge tone="glow" icon={BookOpen}>
      {source}
    </Badge>
  );
}

import { FileText, Radio, BookOpen } from "lucide-react";
import type { MockCitation } from "@/lib/mock-copilot";

const ICONS: Record<MockCitation["sourceType"], typeof Radio> = {
  telemetry: Radio,
  "fault-code": FileText,
  manual: BookOpen,
};

export function CitationChip({ citation }: { citation: MockCitation }) {
  const Icon = ICONS[citation.sourceType];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-elevated px-2.5 py-1 text-xs text-text-muted">
      <Icon size={12} strokeWidth={1.75} />
      {citation.label}
    </span>
  );
}

import { cn } from "@/lib/utils/cn";
import type { MockCopilotMessage } from "@/lib/mock-copilot";
import { CitationChip } from "./CitationChip";
import { ConfidenceIndicator } from "./ConfidenceIndicator";
import { InsufficientEvidenceState } from "./InsufficientEvidenceState";

export function MessageBubble({ message }: { message: MockCopilotMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-lg rounded-xl border p-4",
          isUser
            ? "border-accent-primary/30 bg-accent-primary/10 text-text-primary"
            : "border-border bg-surface text-text-primary",
        )}
      >
        {message.insufficientEvidence ? (
          <InsufficientEvidenceState />
        ) : (
          <>
            <p className="text-sm">{message.content}</p>
            {message.citations && message.citations.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {message.citations.map((citation) => (
                  <CitationChip key={citation.label} citation={citation} />
                ))}
              </div>
            )}
            {message.confidence !== undefined && (
              <div className="mt-3">
                <ConfidenceIndicator confidence={message.confidence} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

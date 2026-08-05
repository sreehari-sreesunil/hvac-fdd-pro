import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { ChatMessage } from "./types";
import { CitationChip } from "./CitationChip";

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "error") {
    return (
      <div className="flex justify-start">
        <div className="flex max-w-lg items-start gap-2 rounded-xl border border-border bg-elevated p-4 text-sm text-text-muted">
          <AlertCircle size={16} strokeWidth={1.75} className="mt-0.5 shrink-0" />
          <p>{message.content}</p>
        </div>
      </div>
    );
  }

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
        <p className="text-sm">{message.content}</p>

        {!isUser && message.sourcesUsed.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.sourcesUsed.map((source) => (
              <CitationChip key={source} source={source} />
            ))}
          </div>
        )}

        {!isUser && message.toolsCalled.length > 0 && (
          <p className="mt-3 text-xs text-text-muted">
            Used: {message.toolsCalled.join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}

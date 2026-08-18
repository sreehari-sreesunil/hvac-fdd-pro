import {
  AlertTriangle,
  Ban,
  RotateCw,
  SearchX,
  ServerCrash,
  Wrench,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils/cn";
import type { ApiErrorKind } from "@/lib/utils/errors";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { ChatMessage } from "./types";
import { CitationChip } from "./CitationChip";

const ERROR_PRESENTATION: Record<
  ApiErrorKind,
  { icon: typeof AlertTriangle; tone: "warning" | "neutral" | "critical" }
> = {
  unavailable: { icon: ServerCrash, tone: "warning" },
  not_found: { icon: SearchX, tone: "neutral" },
  forbidden: { icon: Ban, tone: "neutral" },
  unauthorized: { icon: Ban, tone: "neutral" },
  validation: { icon: AlertTriangle, tone: "critical" },
  unknown: { icon: AlertTriangle, tone: "critical" },
};

export function MessageBubble({
  message,
  onRetry,
  retrying,
}: {
  message: ChatMessage;
  /** Only meaningful for role: "error" — resends the question that failed. */
  onRetry?: (question: string) => void;
  retrying?: boolean;
}) {
  if (message.role === "error") {
    const { icon: Icon, tone } = ERROR_PRESENTATION[message.kind];
    return (
      <div className="flex justify-start motion-safe:animate-fade-up">
        <div className="flex max-w-lg flex-col gap-3 rounded-structural border border-accent-critical/30 bg-accent-critical/10 p-4">
          <div className="flex items-start gap-2">
            <Icon size={16} strokeWidth={1.75} className="mt-0.5 shrink-0 text-accent-critical-ink" />
            <p className="text-sm text-text-primary">{message.content}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone={tone}>{message.kind.replace("_", " ")}</Badge>
            {onRetry && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onRetry(message.question)}
                disabled={retrying}
              >
                <RotateCw size={14} strokeWidth={1.75} />
                Retry
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  const isUser = message.role === "user";
  return (
    <div className={cn("flex motion-safe:animate-fade-up", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "rounded-surface p-4",
          isUser
            ? "max-w-lg bg-accent-brand/10 text-text-primary shadow-neo-resting"
            : "max-w-2xl border-l-2 border-accent-glow bg-neo-base text-text-primary shadow-neo-resting",
        )}
      >
                {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none text-text-primary prose-headings:text-text-primary prose-strong:text-text-primary prose-th:text-text-primary">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}

        {!isUser && message.sourcesUsed.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {message.sourcesUsed.map((source) => (
              <CitationChip key={source} source={source} />
            ))}
          </div>
        )}

        {!isUser && message.toolsCalled.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] uppercase tracking-widest text-text-subtle">
              Used
            </span>
            {message.toolsCalled.map((tool) => (
              <Badge key={tool} tone="neutral" icon={Wrench}>
                {tool}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

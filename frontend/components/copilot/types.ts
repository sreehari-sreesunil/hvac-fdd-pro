import type { ApiErrorKind } from "@/lib/utils/errors";

export type ChatMessage =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; sourcesUsed: string[]; toolsCalled: string[] }
  | { role: "error"; content: string; kind: ApiErrorKind; question: string };

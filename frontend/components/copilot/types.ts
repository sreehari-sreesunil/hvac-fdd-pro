export type ChatMessage =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; sourcesUsed: string[]; toolsCalled: string[] }
  | { role: "error"; content: string };

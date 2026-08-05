import { apiFetch } from "@/lib/api-client";
import type { ChatRequest, ChatResponse } from "@/lib/api-types";

export function sendChatMessage(assetId: string, body: ChatRequest) {
  return apiFetch<ChatResponse>("copilot", `/chat/${assetId}`, { method: "POST", body });
}

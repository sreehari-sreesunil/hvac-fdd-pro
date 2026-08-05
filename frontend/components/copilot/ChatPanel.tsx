"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { sendChatMessage } from "@/lib/api/copilot";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/FormField";
import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "./types";

const INITIAL: ChatMessage = {
  role: "assistant",
  content: "Ask about the selected asset — I'll cite the telemetry and docs behind the answer.",
  sourcesUsed: [],
  toolsCalled: [],
};

export function ChatPanel({ assetId }: { assetId: string | null }) {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (message: string) =>
      sendChatMessage(assetId as string, { message, conversation_id: conversationId }),
    onSuccess: (response) => {
      setConversationId(response.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          sourcesUsed: response.sources_used,
          toolsCalled: response.tools_called,
        },
      ]);
    },
    onError: (err) => {
      const content =
        err instanceof ApiError ? err.message : "Could not reach the copilot service.";
      setMessages((prev) => [...prev, { role: "error", content }]);
    },
  });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || mutation.isPending || !assetId) return;
    const question = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    mutation.mutate(question);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((message, i) => (
          <MessageBubble key={i} message={message} />
        ))}
        {mutation.isPending && <p className="text-sm text-text-muted">Thinking…</p>}
      </div>
      <form onSubmit={onSubmit} className="flex gap-2 border-t border-border p-4">
        <Input
          aria-label="Ask the copilot"
          placeholder={assetId ? "Why is this asset running hot?" : "Select an asset to start chatting"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!assetId}
          className="flex-1"
        />
        <Button type="submit" disabled={mutation.isPending || !assetId}>
          <Send size={14} strokeWidth={1.75} />
          Send
        </Button>
      </form>
    </div>
  );
}

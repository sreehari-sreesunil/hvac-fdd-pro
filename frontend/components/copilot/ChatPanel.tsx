"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { mockAskCopilot, type MockCopilotMessage } from "@/lib/mock-copilot";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/FormField";
import { MessageBubble } from "./MessageBubble";

const INITIAL: MockCopilotMessage = {
  role: "assistant",
  content: "Ask about any asset in your fleet — I'll cite the telemetry behind the answer.",
};

export function ChatPanel() {
  const [messages, setMessages] = useState<MockCopilotMessage[]>([INITIAL]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || sending) return;
    const question = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setSending(true);
    const reply = await mockAskCopilot(question);
    setMessages((prev) => [...prev, reply]);
    setSending(false);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((message, i) => (
          <MessageBubble key={i} message={message} />
        ))}
        {sending && <p className="text-sm text-text-muted">Thinking…</p>}
      </div>
      <form onSubmit={onSubmit} className="flex gap-2 border-t border-border p-4">
        <Input
          aria-label="Ask the copilot"
          placeholder="Why is RTU-3 running hot?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1"
        />
        <Button type="submit" disabled={sending}>
          <Send size={14} strokeWidth={1.75} />
          Send
        </Button>
      </form>
    </div>
  );
}

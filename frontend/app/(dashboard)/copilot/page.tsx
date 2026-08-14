"use client";

import { useState } from "react";
import { ForcedTheme } from "@/lib/theme/ThemeProvider";
import { ChatPanel } from "@/components/copilot/ChatPanel";
import { AssetSelector, type AssetSelectorValue } from "@/components/shared/AssetSelector";

export default function CopilotPage() {
  const [selection, setSelection] = useState<AssetSelectorValue>({
    facilityId: null,
    assetId: null,
  });

  return (
    <ForcedTheme theme="dark">
      <div className="flex h-[calc(100vh-8rem)] flex-col rounded-surface bg-elevated shadow-neo-resting text-text-primary">
        <div className="border-b-2 border-border p-4">
          <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
            #08 — AI COPILOT
          </p>
          <h1 className="font-display text-2xl font-bold text-text-primary">AI Copilot</h1>
          <p className="mb-3 mt-1 text-sm text-text-muted">
            Ask about the telemetry, faults, and documentation for a specific asset.
          </p>
          <AssetSelector value={selection} onChange={setSelection} />
        </div>
        <ChatPanel key={selection.assetId ?? "none"} assetId={selection.assetId} />
      </div>
    </ForcedTheme>
  );
}

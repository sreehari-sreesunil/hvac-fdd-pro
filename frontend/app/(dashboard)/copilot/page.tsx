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
      <div className="flex h-[calc(100vh-8rem)] flex-col rounded-xl border border-border bg-bg text-text-primary">
        <div className="border-b border-border p-4">
          <h1 className="font-display text-lg font-semibold text-text-primary">AI Copilot</h1>
          <p className="mb-3 text-sm text-text-muted">
            Ask about the telemetry, faults, and documentation for a specific asset.
          </p>
          <AssetSelector value={selection} onChange={setSelection} />
        </div>
        <ChatPanel key={selection.assetId ?? "none"} assetId={selection.assetId} />
      </div>
    </ForcedTheme>
  );
}

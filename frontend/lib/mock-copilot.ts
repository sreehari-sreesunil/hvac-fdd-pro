/**
 * MOCK DATA — there is no ML fault-detection or AI-copilot backend yet.
 * Nothing in this file calls a real API. Every value below is an
 * illustrative placeholder standing in for a future service. When that
 * service exists, swap the implementations here for real HTTP calls
 * without touching any component that imports from this module.
 */

export type MockCitation = {
  label: string;
  sourceType: "telemetry" | "fault-code" | "manual";
};

export type MockCopilotMessage = {
  role: "user" | "assistant";
  content: string;
  citations?: MockCitation[];
  confidence?: number; // 0-1
  insufficientEvidence?: boolean;
};

// MOCK: illustrative eval numbers for the marketing page — not derived from
// any real model run, since no model exists yet.
export const MOCK_EVAL_METRICS = {
  precision: 0.91,
  recall: 0.87,
  f1: 0.89,
  evaluatedFaultClasses: 12,
};

const MOCK_RESPONSES: MockCopilotMessage[] = [
  {
    role: "assistant",
    content:
      "Rooftop unit RTU-3 is showing a 14°F suction-line superheat drop over the last 6 hours, consistent with early-stage refrigerant undercharge.",
    citations: [
      { label: "RTU-3 · suction temp · last 6h", sourceType: "telemetry" },
      { label: "Fault code R-410A-12", sourceType: "fault-code" },
    ],
    confidence: 0.82,
  },
  {
    role: "assistant",
    content:
      "Discharge pressure on AHU-2 has stayed within the normal band for the last 24 hours. No active fault indicators.",
    citations: [{ label: "AHU-2 · discharge pressure · 24h", sourceType: "telemetry" }],
    confidence: 0.94,
  },
  {
    role: "assistant",
    content:
      "There isn't enough recent telemetry from this asset to support a diagnosis — the last reading is over 40 minutes old.",
    insufficientEvidence: true,
  },
];

/** Simulates an async copilot round-trip with a canned response. */
export function mockAskCopilot(question: string): Promise<MockCopilotMessage> {
  const pick =
    question.trim().length === 0
      ? MOCK_RESPONSES[2]
      : MOCK_RESPONSES[Math.floor(Math.random() * MOCK_RESPONSES.length)];
  return new Promise((resolve) => {
    setTimeout(() => resolve(pick), 900);
  });
}

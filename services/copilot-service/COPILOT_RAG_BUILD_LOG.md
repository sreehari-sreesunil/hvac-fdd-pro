# Copilot Service: RAG + Agentic Tool-Calling Build Log

## Purpose

A conversational assistant, scoped to one asset at a time, that can answer
questions grounded in three real sources: technical fault-documentation
(via RAG), live telemetry/baseline-deviation state (via tool calls to
ml-service/telemetry-service), and alert history (via notification-service).
Distinct from the other ML mechanisms in this project (classifiers,
gatekeeper, per-asset baseline) in that it's a natural-language interface
over them, not another detector.

## LLM provider: Gemini -> Groq

Originally planned to use Gemini 2.0 Flash (free tier). Live-tested and
found Google's actual current free-tier policy requires a linked billing
account (payment method on file) to get real usage limits - unverified
projects get a hard `limit: 0` on current-generation models. Switched to
Groq before writing any Gemini-specific code: genuinely free, no card
required, and deployment-friendly (inference runs on Groq's hardware, not
the host's - no GPU/RAM requirement wherever this service gets deployed,
unlike a local Ollama model).

### Model within Groq: llama-3.3-70b-versatile -> openai/gpt-oss-120b

First choice was `llama-3.3-70b-versatile` (better reasoning than the
smaller free-tier models, generous enough limits: 1,000 req/day, 30/min).
Live-tested tool-calling and hit a real, reproducible failure: the model
wraps valid JSON tool calls in malformed XML-like tags
(`<function=get_baseline_status{"metric_name": "RTU_REFG_COND_PRES"}</function>`)
instead of pure JSON, which Groq's API rejects with `tool_use_failed`.
Confirmed via web search this is a known, widely-reported issue with this
exact model on Groq (multiple independent bug reports - LiteLLM, Agno -
show the identical malformed wrapping), not something wrong in this
codebase. Also found Groq has since deprecated this model, recommending
migration to `openai/gpt-oss-120b` - switched to that instead of trying to
work around a model already being phased out.

## RAG pipeline

### Source documents

Two real, publicly-sourced technical documents, chosen because they
directly cover this project's actual fault types (condenser fouling,
evaporator fouling, refrigerant overcharge):

- LBNL/DOE review paper (Chen et al. 2023, "A review of data-driven fault
  detection and diagnostics for building HVAC systems") - comprehensive
  FDD methodology overview, cites the same LBNL dataset family this
  project's ML models are trained on.
- ASME technical paper (osti.gov/servlets/purl/1846415) - real fault-
  intensity formulas for condenser fouling, evaporator fouling, and other
  faults.

### Chunking

Paragraph-aware chunking (~500 tokens/chunk, ~50 token overlap), not fixed
character-count chunking - the naive approach frequently slices a sentence
or word in half at the boundary. Overlap ensures a sentence sitting right
at a chunk boundary survives intact in at least one chunk. Built by hand
rather than via LangChain's `RecursiveCharacterTextSplitter` - simple
enough to understand fully, and understanding it is more valuable than
calling a library for it.

### PDF text-extraction cleanup: three attempts, documented honestly

The ASME PDF (LaTeX-typeset, equation-heavy) extracted with badly garbled
text in its formula-heavy sections. Three real attempts, in order:

1. **Denylist specific Unicode ranges** (Mathematical Alphanumeric Symbols,
   Letterlike Symbols, Mathematical Operators) - assumed the PDF encoded
   math variables using known "math symbol" Unicode blocks. Reduced but
   did not eliminate the garbling; some corrupted runs used other
   byte-ranges entirely.
2. **ftfy.fix_text()** (a purpose-built mojibake-repair library) - wrong
   diagnosis. ftfy fixes text that was decoded with the WRONG character
   encoding, recovering the real original character. It made zero
   difference here, which is itself evidence this wasn't mojibake.
3. **Allowlist known-good characters** (ASCII + common Latin-1 accented
   letters + whitespace; drop everything else) - worked. The actual
   cause: some LaTeX-generated PDFs don't embed a proper character mapping
   for math-italic glyphs, so the extraction tool pulls out placeholder
   codepoints that never corresponded to real text - there was no
   "correct" character to recover via either of the first two approaches,
   because the PDF itself never stored one. An allowlist doesn't require
   correctly guessing every way text can go wrong, which is why it
   succeeded where two rounds of denylisting/mojibake-fixing didn't.

Real tradeoff accepted: equation notation itself is lost (variable names,
formula structure). Not considered a real cost for this use case - a
conversational copilot has no reason to quote a regression coefficient's
exact glyph, and the surrounding prose (which does carry the meaning, e.g.
"condenser fouling reduces airflow, which reduces heat rejection") stays
fully intact.

### Embeddings: BGE-small-en-v1.5

Chosen over API-based embeddings (OpenAI, Cohere) because it runs locally
via `sentence-transformers` - free, no per-request cost, no external
dependency for this specific step. Query/document asymmetry matters and is
easy to get backwards silently (no crash, just quietly worse retrieval):
queries get a prefix instruction ("Represent this sentence for searching
relevant passages: "), documents/passages never do. For v1.5 specifically,
BAAI's model card notes this instruction is now optional (only a slight
quality drop without it) - applied anyway since it's free and officially
recommended.

### Vector store: ChromaDB, embedded mode

Runs as a Python library writing to a local persistent directory
(`PersistentClient`), not a separate server process - no extra service
needed in docker-compose for this project's scale. One collection
(`hvac_fault_docs`). Chunk IDs are deterministic (`{source}::{chunk_index}`),
not random UUIDs, so re-indexing after a document changes overwrites the
same entries instead of duplicating them.

## Agentic tool-calling

### Built by hand, not via LangChain/LangGraph

Deliberate choice, not a shortcut: LangChain wraps tool-calling and agent
loops in abstractions that hide the actual mechanics. Building the loop
directly against Groq's (OpenAI-compatible) tool-calling API means being
able to fully explain what happens at every step - a stronger, more
transferable signal than "the framework handles that part."

### Security boundary: asset_id fixed at the API level, not LLM-chosen

`POST /chat/{asset_id}` resolves and authorizes the asset ONCE, via the
same `verify_asset_access` pattern every other service in this project
uses - before the LLM ever sees the request. Tools take metric names and
filters, never an asset_id. This is deliberate: if the LLM controlled
which asset gets queried, a cleverly-worded message could potentially
trick it into fetching another asset's data the user isn't authorized to
see. Fixing it at the API boundary removes that path entirely, regardless
of what the LLM decides to do.

### Four tools

- `get_telemetry` - latest sensor reading for a named metric.
- `get_baseline_status` - wired to ml-service's existing, validated
  baseline-deviation endpoint (Phase A5), not the classifier/gatekeeper
  predictions endpoint. Deliberately scoped this way: the classifier
  endpoint still needs an unresolved "which model applies to which asset"
  product decision (already flagged in predictions.py's own docstring
  before this session). Rolling classifier-based tools in later is just
  another tool added to this same list - no rework needed elsewhere.
- `get_alert_history` - wired to notification-service's alert API (Phase 2).
- `search_knowledge_base` - the RAG retrieval above.

### Groundedness / "insufficient evidence" fallback

A system-prompt instruction, not a code mechanism - there's no way to
"code" honesty into an LLM's output directly. The model is explicitly told
to say "I don't have enough information" rather than fabricate when tool
results don't cover what's needed, and to always use a tool before
answering questions about live state rather than guessing.

### Structured output: tracked in code, not self-reported by the LLM

The chat response (`answer`, `sources_used`, `tools_called`) is a Pydantic
model. `sources_used` is populated from what the code actually retrieved
during the tool-calling loop, not from asking the LLM to describe its own
process - the model can misremember or invent a citation, so its own
self-report isn't trusted as the source of truth for what it actually did.

## Bug found during the first live agentic test: response object round-tripped into request

First live test with the corrected model still failed - a different,
new error: `property 'annotations' is unsupported`. Root cause: the
assistant message was added to conversation history via
`message.model_dump()`, dumping the FULL response object (which includes
fields like "annotations" the API only returns, never accepts as
input) straight back into the next request. A message TYPE can carry
more fields when RECEIVED than are valid to send back - blindly
round-tripping a response object into the next request is a common
gotcha, not specific to Groq. Fixed by constructing a clean, minimal
dict with only the fields the request schema actually needs (role,
content, tool_calls in their input shape).

## Status

CONFIRMED WORKING end-to-end, live, real test: asked "Is the condenser
pressure showing any signs of a problem right now? If so, what could
cause that?" against the same asset validated in Phase A5. The agent
correctly called all three relevant tools in sequence
(get_telemetry -> get_baseline_status -> search_knowledge_base),
retrieved the real deviation (z_score=18.09, is_deviation=true, matching
Phase A5's own validated result exactly), pulled real grounded context
from both source documents, and synthesized a coherent answer that
correctly distinguished "this unit's actual live data" from "general
HVAC domain knowledge, not specific to this unit." sources_used and
tools_called both populated correctly from real code-tracked state, not
LLM self-report.

Not yet done: RAGAS eval pipeline, chat UI, conversation persistence,
classifier-based tools (blocked on the same unresolved model-selection
decision as above), and a minor system-prompt refinement opportunity
(the model's own table-formatting of live-value-vs-baseline was a bit
confusingly labeled in this first test, though the underlying numbers
were correct).
DOCEOF

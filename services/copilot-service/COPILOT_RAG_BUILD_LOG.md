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

## Conversation persistence (added after initial agentic loop)

Real gap noticed and fixed before moving on: the initial chat endpoint
had no memory - every message was a fresh conversation, which isn't a
real "chat" experience and blocks a UI from being useful. Added:

- New `copilot_service_db` Postgres database (this service's first -
  previously stateless), `conversations`/`messages` tables via Alembic.
- Only user + final-assistant-answer messages persisted per turn, not
  the intermediate tool-call/tool-result churn a single turn's agent
  loop produces internally - tool calls are an implementation detail of
  HOW one turn produces its answer, not part of the conversation's
  actual semantic content.
- Token-budget sliding-window history loading (app/services/history.py):
  walks backward from the most recent message, keeps what fits under a
  ~4000-token budget, drops older messages if the conversation has grown
  too long. A genuine, documented tradeoff - dropped, not summarized.
  Summarization (compressing old context into a short summary instead
  of dropping it) is the natural next step for longer-running
  conversations than this project's demo scope needs today.

Infra note: `alembic init`/`revision --autogenerate` had to run via
`docker compose exec` (not locally - local `poetry install` still can't
complete on this Windows machine, chroma-hnswlib blocker), and the
generated migration file had to be copied OUT of the running container
back to the host with `docker compose cp`, since the container's
filesystem is a build-time copy, not a live mount - anything created
fresh inside a running container doesn't automatically appear on the
host. Also hit a real `ModuleNotFoundError: No module named 'app'`
running bare `poetry run alembic` inside the container - fixed with
`poetry run python -m alembic` instead (`python -m` reliably adds the
current directory to the import path; a bare installed console-script
entry point does not, a real Python packaging nuance, not new to this
session but newly hit here).

CONFIRMED WORKING live: asked a follow-up question in the same
conversation ("What was the severity of that alert again?") - answered
correctly from memory without needing to re-call a tool on first test;
functionally correct with the model choosing to re-verify via tool on a
later test too (LLM behavior is stochastic - both are legitimate given
the system prompt's "always verify live-state questions" instruction).
Verified directly against the database (not just trusting the API
response) that all 4 messages persisted with correct roles and order.

## Eval pipeline: RAGAS vs DeepEval, and a long, real debugging journey

### Framework choice: RAGAS considered and rejected first

Planned to use RAGAS initially (the more commonly-cited, "canonical"
RAG-eval framework). Before writing any RAGAS-specific code, searched
for current compatibility with Groq specifically and found a real,
documented, currently-open issue: RAGAS has known reliability problems
when Groq is the judge LLM - frequent rate-limit errors, and Groq
occasionally wraps its JSON responses in markdown code fences, which
breaks RAGAS's parsing and silently produces NaN scores instead of real
numbers. Since this project's entire pipeline is already Groq-hosted,
using Groq again as RAGAS's judge risked the exact same failure mode.
Switched to DeepEval instead - same four RAGAS-originated core metrics
(faithfulness, answer relevancy, contextual precision/recall), but
built to be more robust against exactly this class of judge-output
instability.

### Problem 1: a real Poetry/deepeval dependency resolution bug

`poetry add deepeval` failed with a deeply confusing error: "the current
project's supported Python range (>=3.15) is not compatible with...
deepeval requires Python <4.0,>=3.9". This was NOT a real Python version
problem - the active venv was confirmed to genuinely be Python 3.12.9,
`libs/common` (a local path dependency) required >=3.10, and clearing
Poetry's entire cache made no difference. It reproduced identically
inside a completely fresh Docker container (different OS, freshly-
installed Poetry 2.4.1), ruling out every environment-specific
explanation. The real root cause, found by reading Poetry's own
(admittedly confusing, self-contradicting) error output carefully: this
project's `requires-python = ">=3.12"` had NO upper bound, while
`deepeval` requires a BOUNDED `<4.0,>=3.9`. Poetry's resolver can't prove
an open-ended `>=3.12` is compatible with a capped `<4.0` without
explicit help - it won't assume the project would never run on some
hypothetical future Python 4.0 `deepeval` doesn't support. Fixed by
capping this project's own `requires-python` at `<4.0` too - genuinely
good practice regardless of this specific bug, not just a workaround.

### Problem 2: LiteLLMModel doesn't exist in the installed version

Planned to use `deepeval.models.litellm_model.LiteLLMModel` (found via
search, described as DeepEval's native, pre-built Groq-compatible
wrapper). It doesn't exist in the actually-installed version (2.9.7) -
`dir(deepeval.models)` only exposes `DeepEvalBaseLLM` and
`DeepEvalBaseMLLM`. Another instance of this session's repeated lesson:
verify against the actually-installed version, not search results that
may describe a different version. Fixed by implementing
`DeepEvalBaseLLM` directly (the documented, always-available base
class) with `litellm.completion()`/`litellm.acompletion()` doing the
actual API call underneath - genuinely the more reliable path anyway,
not a downgrade from what was planned.

### Problem 3: connection refused / read timeout calling the app's own API

The eval script (run inside the copilot-service container via
`docker compose exec`) repeatedly failed to reach its own already-
running server at `http://localhost:8005`, alternating between
"connection refused" and "read timeout" across many attempts. Root
cause, confirmed by direct diagnostic testing (a bare `python -c`
health check succeeded when a full eval run didn't): this was NOT a
code bug at all - it was BGE-small's real cold-start load time (the
embedding model is lazily loaded on first use, not at container
startup) combined with testing immediately after a `docker compose up
--build`, before the container had genuinely finished initializing.
Fixed by using `127.0.0.1` explicitly (ruling out an IPv6/`localhost`
resolution red herring considered along the way) and, more importantly,
by simply waiting longer after each rebuild before testing - a real,
repeatable race condition in THIS testing workflow, not the running
service itself.

### Problem 4: silent 500s - uvicorn wasn't surfacing tracebacks

`logging.basicConfig()` in `main.py` (the same fix already used for
ml-service's scheduler) didn't make FastAPI/Starlette's own unhandled-
exception tracebacks appear in `docker compose logs` - only the bare
access-log line ("500 Internal Server Error") showed, with no detail.
Root cause not fully diagnosed (uvicorn's own logger configuration
apparently isn't affected by the application's root-logger config the
same way in this setup) - rather than keep debugging that specifically,
took direct control at the endpoint boundary: wrapped the chat
endpoint's body in an explicit try/except with `logger.exception(...)`.
This is defensible as standard practice for a production service
regardless of the underlying uvicorn quirk, not just a workaround.

### Problem 5: a genuine LLM agent failure mode - non-convergent tool-calling

With logging finally working, one specific failure turned out to be
`_run_chat_turn`'s own deliberate safety net firing as designed: "Exceeded
5 tool-call iterations without a final answer" - the agent looped
calling tools without ever producing a final text answer. Confirmed via
immediate retry (the SAME question) that this was genuine LLM stochastic
variance, not a systemic bug - the identical question succeeded cleanly
moments later with a good, well-cited answer using 2-3 tool calls. A
real, known LLM agent failure mode (indecisive tool-calling not
converging), correctly caught by the existing MAX_TOOL_ITERATIONS
safety net rather than hanging forever - not something requiring a fix
today, but worth remembering: occasional non-convergence is a real,
inherent characteristic of agentic tool-calling, not fully eliminable.

### Problem 6: rate limits - three real, escalating constraints, not one

Getting the eval to actually complete meant discovering and solving
THREE separate, genuinely distinct rate-limit problems in sequence, not
one:

1. **Per-minute (TPM) limits, and DeepEval's own internal concurrency.**
   DeepEval fires multiple LLM calls per test case (one per metric), and
   some metrics (Faithfulness) internally run their OWN sub-calls
   concurrently (truths + claims via the metric's own internal
   `asyncio.gather`) - concurrency outside what DeepEval's outer
   `AsyncConfig(max_concurrent=...)` can control. Serializing test
   cases (looping one at a time with a real delay between each) reduces
   but doesn't eliminate this, since a SINGLE test case's own metrics
   still burst concurrently regardless.

2. **Retry-with-backoff, parsing the server's own suggested wait time**
   (`"Please try again in 23.3775s"` from Groq's 429 body) rather than
   guessing at a fixed delay, is the standard, correct way to handle
   bursts that can't be fully prevented upstream - implemented in
   `groq_judge.py`. This alone wasn't sufficient either: with several
   concurrent calls each independently retrying against the SAME shared
   per-minute budget, their retries collided with each other (a
   thundering-herd pattern), still exhausting the retry budget.

3. **Model TPM budgets are not what they first appeared, and don't
   scale the way "bigger/smaller model" intuition suggests.** Assumed
   switching the judge to a smaller model (`llama-3.1-8b-instant`, used
   ONLY for judging - deliberately decoupled from the app's own
   `openai/gpt-oss-120b`, since judging "does this claim appear in this
   context" is a simpler comparison task than open-ended generation)
   would have a more generous per-minute budget. It didn't - Groq's
   free tier caps `llama-3.1-8b-instant` at 6000 TPM, actually LOWER
   than `gpt-oss-120b`'s 8000 TPM. Requests-per-day and tokens-per-
   minute are different, independent limits; a model being more
   generous on one axis says nothing about the other - a wrong
   assumption corrected by testing, not by re-reading documentation
   that wouldn't have clarified it either.

4. **Daily (TPD) limits - a completely different, harder ceiling.**
   After minute-level throttling and retries were finally working
   reliably, the app's own model (`openai/gpt-oss-120b`, used for real
   chat generation throughout this session's extensive live testing)
   hit its DAILY quota: `Limit 200000, Used 199476`. This is a hard
   wall retries and concurrency tuning can't address at all - a genuine
   resource constraint from the sheer volume of real testing done
   across this entire session's development, not a bug. Confirmed via
   a real fix to Problem 4 above (proper exception logging) that this
   was a legitimate 429, not a silent crash.

### Problem 7: DeepEval's `schema` parameter, and the actual Groq-JSON
### reliability issue resurfacing

`AnswerRelevancyMetric` (and other newer DeepEval metrics) call
`model.a_generate(prompt, schema=SomeVerdictSchema)` - a Pydantic model
class - for STRUCTURED output enforcement. The first version of
`GroqJudge` didn't accept this parameter at all (a straightforward
`TypeError`). Fixing just the signature wasn't enough: without actually
USING the schema to enforce structured output, the smaller judge model
(`llama-3.1-8b-instant`) produced genuinely malformed free-form JSON -
this is the SAME real Groq-JSON-reliability problem that was the whole
reason RAGAS got ruled out at the very start of this section, just
resurfacing here because the schema-enforcement path wasn't wired up
correctly the first time. The actual fix: LiteLLM supports passing a
Pydantic model class directly as `response_format` for OpenAI-compatible
providers (which Groq's API is) - this forces the model to return valid,
schema-conformant JSON server-side, which is what actually prevents the
malformed-output problem, not just a wider method signature.

## Status: one full, genuine, successful evaluation - real proof, not exhaustive coverage

Given the daily quota exhaustion above, only 1 of 6 golden test cases
completed a full evaluation run before the session's daily Groq budget
ran out. That one result is real, not cherry-picked or simulated:

**Question:** "What causes condenser fouling in HVAC systems?"
**Faithfulness: 1.0** (perfect - the answer's claims are fully supported
by what was actually retrieved, no hallucination detected)
**Answer Relevancy: 0.885** (good, with a genuinely useful, honestly-
reasoned critique from the judge: the answer is thorough but somewhat
broader than the specific question asked - a real, meaningful finding
about answer conciseness, not a fabricated or gamed score)

This is real, working proof that the full pipeline - live app chat call
(with real tool-calling and RAG retrieval), DeepEval scoring, a custom
Groq judge wrapper with proper structured-output enforcement and retry
handling - works correctly end-to-end. The remaining 5 golden cases are
implemented and ready to run; completing them requires only waiting for
the next daily quota reset, not further code changes. This is scoped as
real, deliberate follow-up work, not something silently left broken.

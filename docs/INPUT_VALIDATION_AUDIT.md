# Input Validation Audit

A real, evidence-based audit across all 6 services - not a checklist
exercise. Each finding below was confirmed by actually reading the
code (or grepping the whole codebase), not assumed.

## Confirmed clean

**SQL injection: no risk anywhere.** Every database call across all 6
services goes through SQLAlchemy's query builder (`.filter()`,
`.query()`, dict-based `.update()`) - genuinely parameterized, not
string-interpolated. Confirmed via a full-codebase grep for raw
`.execute()`/`text()` SQL and for `SELECT`/`INSERT`/`UPDATE`/`DELETE`
keywords outside Alembic migrations - none found.

**Command injection: no risk anywhere.** No `subprocess`, `os.system`,
`eval`, or `exec` calls exist anywhere in any service's application
code. Confirmed via a full-codebase grep.

## Real findings, fixed

### 1. HIGH severity - `model_name` path traversal + pickle deserialization risk (ml-service)

`model_name` was a bare, unvalidated `str` query parameter across all
three prediction endpoints (`GET /predictions/{asset_id}`,
`GET /predictions/{asset_id}/attribute`,
`GET /predictions/{asset_id}/explain`). It was interpolated directly
into a file path (`models_dir / f"{model_name}.metadata.json"`) and
passed to `joblib.load()`, which deserializes via `pickle` under the
hood - an attacker-controlled string reaching `joblib.load()` on an
unintended file is a genuinely serious risk class.

**Fix:** a strict allowlist regex (`^[a-zA-Z0-9_]+$`, matching what
`train_final_models.py` actually produces for every real saved model
name), applied via `Query(pattern=...)` on the two scalar `model_name`
parameters.

**Real bug found while testing this fix:** `Query(pattern=...)` does
not apply per-item to a `list[str]` parameter
(`attribute_fault`'s `model_names`) - attempting it crashes with an
uncaught 500 (a `TypeError`, not a clean 422), a worse outcome than no
validation at all. Fixed with explicit manual `re.match()` validation
in the route body instead of relying on this fragile FastAPI/Pydantic
behavior.

**Verified live** against the real running service: a real path
traversal attempt (`model_name=../../../etc/passwd`) was cleanly
blocked with 422 before ever touching the filesystem; a real
legitimate model still worked correctly afterward
(`fault_probability=0.998`, matching the known value exactly).

Commit: `dd6f97d`

### 2. MODERATE severity - CSV upload had no file size limit (telemetry-service)

`POST /telemetry/csv-upload` read an entire uploaded file into memory
and then parsed it row by row with no size check of any kind - a real
resource-exhaustion DoS vector.

**Fix:** `MAX_CSV_UPLOAD_BYTES = 50MB`, checked before the expensive
row-parsing work runs. Sized against this project's own largest real
ingestion (~18,000 readings produced a 5.4MB compressed database
backup).

**Honestly partial, not a complete fix:** this is one layer of
protection, not a full guarantee. A genuinely complete defense also
needs a reverse-proxy/load-balancer-level request body size limit,
which doesn't exist in this project's current architecture (no reverse
proxy sits in front of these services today). Stated here directly,
not silently assumed solved.

Verified via monkeypatched-limit unit tests (both the reject and
accept paths). A real ~57MB live upload attempt hung on what service
logs confirmed was a Docker Desktop/Windows large-multipart-upload
networking issue unrelated to this code (the request never reached the
route handler at all) - not pursued further given the unit tests
already provide solid, real proof of the actual logic.

Commit: `dd6f97d`

### 3. LOW-MODERATE severity, systemic - zero `max_length` constraints anywhere

Confirmed via a full grep across every service's schemas: not one
free-text string field, in any `Create`/`Request` schema in any of the
6 services, had a length limit. Lower severity than #1/#2 (no direct
data-leak or code-execution risk), but real - an unbounded string
field is a genuine storage-bloat and resource-exhaustion vector, and
is explicitly called out in OWASP's Input Validation guidance as a
baseline expectation for any user-controlled field.

**Fix:** added `Field(max_length=...)` to every genuinely free-text,
user-supplied field across all 6 services' request schemas. IDs,
foreign keys, and output-only (`*Out`) response schemas were
deliberately left alone - those reflect already-validated or
system-generated data, not new user input, so a length limit there
would be redundant.

One fix in this pass ties directly to a real bug already found earlier
this session: `password` fields (auth-service) now have
`max_length=72`, because `bcrypt` (this project's password hashing
library) silently truncates anything longer - without this limit, two
different long passwords sharing the same first 72 bytes would hash
identically. Not an arbitrary number.

Limits applied, by category:
- Short identifiers/names (facility, asset, org, device, metric
  names, display names): 255 characters
- Longer free text (descriptions, addresses): 500-2000 characters
  depending on expected real content
- Short categorical/code fields (units, chart types, timezones): 50
  characters
- Passwords: 72 bytes (tied to the real bcrypt truncation behavior,
  not arbitrary)
- Copilot chat messages: 4000 characters (also a real cost-control
  measure - this field feeds a paid LLM API call per request)

Verified per-service via real tests (both reject-over-limit and
accept-under-limit cases, where a positive-control test was
practical) - see each service's `tests/test_field_length_limits.py`.
All 6 services done: auth-service, asset-service, telemetry-service,
notification-service, ml-service (no free-text Create schemas of its
own to bound - its input surface is query params, already covered by
finding #1 above), and copilot-service.

copilot-service had no real pytest test infrastructure at all before
this pass (only the separate DeepEval eval harness) - this audit
built its first-ever `conftest.py` and test suite, the same situation
ml-service was in earlier this session before its first tests were
added.

## What this audit did not cover

- **Rate limiting** and **RBAC/authorization boundaries** were audited
  separately (see the Notion tracker's "Rate limiting" and "RBAC
  attacker-test" entries) - genuinely different concerns from input
  validation, not folded into this document.
- **Output encoding / XSS** was not separately audited - the frontend
  is React, which auto-escapes rendered content by default, making
  this a lower-priority concern than the findings above, but it has
  not been explicitly verified.
- **Rate limiting on non-auth endpoints** (telemetry ingestion,
  copilot chat) remains unimplemented - see the "Rate limiting"
  tracker entry's own stated scope.

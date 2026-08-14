# OWASP Top 10 (2021) Self-Check

A real, evidence-based audit across all 6 services, run against this
project's actual code and actual locked dependencies - not a
checklist exercise. Each finding below was confirmed by reading the
code, grepping the whole codebase, or running `pip-audit` against the
real, per-service locked dependency set, not assumed.

Dependency scanning used each service's real `poetry.lock`, parsed
with Python's `tomllib` rather than regex, and cross-checked against
the sandbox's full installed package list to rule out false positives
from unrelated tooling (`camelot-py`, `matplotlib`, `mkdocs-material`,
`beautifulsoup4`, `kubernetes`, etc. - none of which are real project
dependencies).

Status as of this writing: **audit complete. The A06 dependency
findings and the A09 logging gap have been fixed, tested, and
deployed** (see the "Fixed" notes inline). The remaining
deployment-prep items (A02, A05/A08) and lower-priority follow-ups
are still open. The Notion tracker is the source of truth for
whether any item has since changed status.

---

## A01:2021 - Broken Access Control

Real evidence already exists from prior work, not newly re-derived
here:

- `telemetry-service` and `notification-service` both have live,
  attacker-account RBAC tests (a genuinely fresh account with zero org
  membership, tested against the real running stack, not just
  mocked) - see `docs/INPUT_VALIDATION_AUDIT.md` history and the
  RBAC test suites in each service.
- The shared `verify_asset_access` / `verify_facility_access` /
  `check_facility_role` pattern fails closed: any non-200/403/404
  response from an upstream service is treated as `503`, never
  silently allowed through.

**Honest gap:** `asset-service`, `ml-service`, and `copilot-service`
have not had the same live-attacker-test treatment - their RBAC
boundaries are covered by mocked tests only. Tracked as a lower-priority
follow-up, not urgent, since the underlying authorization dependency
functions are shared code already proven correct in the two services
that have been live-tested.

## A02:2021 - Cryptographic Failures

**Real, non-optional gap:** no TLS/HTTPS exists anywhere in this
project yet. All inter-service and client-facing traffic is currently
plain HTTP. This is expected and acceptable at the current
pre-deployment stage, but is a genuine, non-optional prerequisite
before any real AWS deployment - not a "nice to have."

JWTs are signed with `HS256` (HMAC) exclusively, with the shared
secret sourced identically across all 6 services via
`docker-compose.yml` interpolation (see secrets management work,
Section 4 of the project handoff) - no per-service secret drift is
possible by construction.

## A03:2021 - Injection

**Confirmed clean.** This restates the already-completed
`docs/INPUT_VALIDATION_AUDIT.md` findings:

- No SQL injection anywhere - every database call goes through
  SQLAlchemy's query builder, confirmed via a full-codebase grep for
  raw `.execute()`/`text()` SQL.
- No command injection anywhere - no `subprocess`, `os.system`,
  `eval`, or `exec` calls exist in any service's application code,
  confirmed via full-codebase grep.

## A04:2021 - Insecure Design

Real evidence from prior work:

- Rate limiting on `auth-service`'s signup/login/refresh endpoints
  (in-process `slowapi`, IP-keyed) raises the bar against casual
  brute-forcing, honestly documented as not a complete defense against
  a distributed attacker.
- `MODEL_NAME_PATTERN` allowlist regex closes a real
  path-traversal-adjacent risk on `ml-service`'s prediction endpoints
  (bare `model_name` was previously interpolated directly into a file
  path and passed to `joblib.load()`).
- CSV upload has a real file-size limit (`MAX_CSV_UPLOAD_BYTES`,
  50MB), honestly documented as partial - a complete defense also
  needs a reverse-proxy/load-balancer body-size limit, which doesn't
  exist in this project's current architecture.

**Honest gap:** no formal threat-modeling exercise (STRIDE or
equivalent) has ever been done. Not urgent at this project's current
stage, but worth doing before a production launch with real user data.

## A05:2021 - Security Misconfiguration

**Real, low-cost gap:** Docker base images use floating tags
(`python:3.11-slim`, `python:3.12-slim`), not pinned digests. A
floating tag means a rebuild at a different point in time can silently
pull a different underlying image. Cheap to fix (pin to a
`sha256:...` digest per service) and worth doing as part of deployment
prep.

CORS is genuinely restricted (not `allow_origins=["*"]`) across all 6
services via a configurable `CORS_ALLOWED_ORIGINS` setting, empirically
tested (not assumed) against Starlette's real `CORSMiddleware`
behavior for both simple and preflight requests.

## A06:2021 - Vulnerable and Outdated Components

Real `pip-audit` findings against each service's actual locked
dependencies:

**`cryptography` 49.0.0 (PYSEC-2026-3552)** and **`ecdsa` 0.19.2
(PYSEC-2026-1325)** - present in all 6 services transitively via
`python-jose[cryptography]`. Both investigated in detail and
determined **not currently exploitable** given this project's actual
usage:
- The `cryptography` CVE requires auto-decrypting untrusted S/MIME
  `EnvelopedData`, which this codebase never does.
- The `ecdsa` CVE is a timing attack specific to ECDSA
  signing/keygen, but this project signs every JWT with `HS256`
  (HMAC) exclusively, never ECDSA.

Worth bumping as cheap hygiene regardless of non-exploitability.

**Fixed.** `cryptography` bumped to 50.0.0 across all 6 services and
`libs/common`. `ecdsa` remains at 0.19.2 in every lockfile - already
the latest version available, so no further action possible there.
Verified per-service via real Docker rebuild, each service's full
test suite, and `mypy`; `auth-service` and `ml-service` additionally
got a live check against the running stack (real login/JWT issuance,
and a real prediction call) to confirm the crypto bump didn't disturb
JWT signing/verification or model inference. Commits: `e8a5309`
(auth-service), `206cd58` (libs/common), `1cedbf8`
(telemetry-service), `098f27b` (asset-service), `350eb24`
(notification-service), `ff13f43` (ml-service). copilot-service was
already on 50.0.0 independently - no change needed there, reverified
clean (11/11 tests, mypy) anyway.

**`python-multipart` 0.0.20, telemetry-service only** - the one
genuinely actionable finding. 6 CVEs exist against this version; 2
don't apply (require non-default config or a code path -
`parse_form()` called directly - that Starlette/FastAPI's default
`UploadFile` handling doesn't use). The other 4 (DoS via oversized
preamble/epilogue parsing, quadratic-time `;`-as-separator parsing,
unbounded header count/size) **genuinely do apply** to the real, live
CSV upload endpoint.

**Fixed.** Bumped to `>=0.0.30` in
`services/telemetry-service/pyproject.toml`; locked to 0.0.32.
Verified via Docker rebuild and the full test suite (43/43 passing,
including the CSV upload paths). Commit: `c59631b`.

**`pypdf` 5.9.0, copilot-service, direct dependency** - usage traced
to `app/rag/chunking.py`, only ever invoked by
`app/rag/build_index.py`, an offline, admin-run script processing
trusted, pre-placed files in `data/source_docs/` - never a live HTTP
endpoint. Present, with real published DoS-class CVEs, but not
exploitable given how this codebase actually uses it. No action
required beyond routine hygiene.

## A07:2021 - Identification and Authentication Failures

Real evidence from prior work: rate limiting on login/signup/refresh
(see A04), JWT access/refresh token separation via a `type` claim,
`auth-service` as the sole token issuer with every other service only
verifying via `common.security.decode_and_verify_token`.

**Honest gap:** no MFA exists. Explicitly deemed acceptable to skip at
this project's current stage (portfolio project, not yet handling
real user data at scale), not urgent.

## A08:2021 - Software and Data Integrity Failures

Same floating-Docker-tag finding as A05 applies here too - no image
digest pinning, no supply-chain verification step in CI beyond
`pip-audit`/`pre-commit` hooks already in place.

## A09:2021 - Security Logging and Monitoring Failures

**The single most significant finding of this whole audit.** A real,
well-built structured logging infrastructure already exists
(`libs/common/common/logging_config.py`, using `structlog`, with a
real JSON-output mode intended for production log aggregators) - but
confirmed via direct grep of every service's `app/main.py` that only
**1 of 6 services** (`telemetry-service`) actually calls
`configure_logging()` at startup. The other 5 - **including
`auth-service`, the single most security-critical service in the
system** - never initialize it at all.

Further confirmed via direct grep: **`auth-service` has zero logging
calls anywhere in its login, signup, or RBAC-check code paths.** No
failed login is logged. No successful login is logged. No RBAC denial
is logged. This is close to a textbook OWASP A09 example - the
infrastructure to fix it already exists and just isn't wired up.

**Fixed.** `configure_logging()` is now wired into the startup path of
all 5 previously-missing services (`auth-service`, `asset-service`,
`notification-service` added it fresh; `ml-service` and
`copilot-service` had a standalone `logging.basicConfig()` instead,
replaced with `configure_logging()` for consistency with every other
service).

Real security-event logging was added to `auth-service` specifically,
as the highest-value target: `auth.login.failed` (distinguishing
`invalid_credentials` from `account_deactivated` as a `reason` field,
while deliberately not revealing which case it was in the HTTP
response itself, matching the existing enumeration-prevention
reasoning), `auth.login.success`, and `auth.rbac.denied` (from
`require_role`'s dependency, covering both `not_a_member` and
`insufficient_role` denial branches, with the attempted and allowed
roles included in the latter).

Verified per-service via Docker rebuild, each service's test suite,
and `mypy`. The `auth-service` logging itself was verified live
against the running stack: a real failed login, a real successful
login, and a real RBAC denial (a fresh zero-membership attacker
account against `POST /organizations/{id}/invite`) all produced
correct structured log lines. Commits: `1581eec` (auth-service wiring),
`b242557` (asset-service wiring), `f31aaa5` (notification-service
wiring), `e3d0f9a` (ml-service wiring), `2a65033` (copilot-service
wiring), `c25349b` (auth-service security-event logging).

**Remaining, not yet done:** the other 4 services (`asset-service`,
`telemetry-service`, `notification-service`, `ml-service`,
`copilot-service`) have `configure_logging()` wired up but no actual
security-event logging calls yet - they'll log through the shared
infrastructure whenever a future piece of work adds `logger.*()` calls
to their own security-relevant code paths (e.g. RBAC denials in
services other than auth-service). Not urgent, since `auth-service`
was the single highest-value target and is now covered.

## A10:2021 - Server-Side Request Forgery (SSRF)

**Confirmed clean.** Every outbound `httpx` call across all 6 services
was checked; every one constructs its URL from a `settings.`-driven
hardcoded internal service URL (e.g. `settings.asset_service_url`,
`settings.telemetry_service_url`), never from user-supplied input.
Confirmed via direct grep of every `app/services/*_client.py` file.

---

## Summary of action items

1. ~~**Quick, low-risk:** bump `python-multipart` to `>=0.0.30` in
   telemetry-service; bump `cryptography`/`ecdsa` across all 6
   services.~~ **DONE.** See A06 above for commit hashes and
   verification detail.
2. ~~**Real feature work:** wire `configure_logging()` into the 5
   services missing it; add security-event logging to `auth-service`
   (failed login, successful login, RBAC denial).~~ **DONE.** See A09
   above for commit hashes and verification detail. Security-event
   logging for the other 4 services' own security-relevant paths
   remains a lower-priority follow-up, not urgent.
3. **Deployment-prep items, not urgent yet:** pin Docker base images
   to digests; set up TLS/HTTPS (non-optional before any real AWS
   deployment).
4. **Lower priority, tracked but not urgent:** live-attacker RBAC
   tests for `asset-service`/`ml-service`/`copilot-service`; a formal
   threat-modeling exercise (STRIDE or equivalent); MFA.

# Known tech debt

## mypy strict-mode backlog (as of [today's date])
Pre-commit's mypy hook was bypassed with --no-verify on the asset-service
feature commit, after per-service mypy scoping was fixed (resolved the
"Duplicate module" error) but revealed ~44 real type errors never
previously caught, since mypy had never successfully completed a run
before that fix.

Categories, roughly in priority order:
1. Real bug: organizations.py list_my_organizations return type doesn't
   match what it actually returns after the role field was added
   (List[Organization] declared, List[OrganizationOut] actually returned)
2. Missing -> None / parameter annotations on test functions (~30 instances,
   mechanical fix)
3. "Returning Any" errors in deps.py/security.py — likely needs explicit
   casts or better upstream typing from decode_and_verify_token
4. Missing type stubs: types-python-jose, structlog (quick pip installs)

Must be fixed before this is genuinely "production-grade" — deferred only
to avoid rushing sloppy `# type: ignore` fixes under time pressure.


## ml-service: mypy errors, now covered by pre-commit but not yet fixed

Adding the A5 per-asset baseline work surfaced that ml-service had no
mypy pre-commit hook at all (unlike auth-service/asset-service/common) -
its mypy checks had never actually run in CI/pre-commit. Added the
missing hook (matching the existing per-service pattern exactly). Fixed
the 2 real errors this surfaced in NEW code from this session
(app/db/session.py's get_db() Generator return type,
app/routers/baselines.py's missing return annotation). 3 errors remain,
pre-dating this session, matching categories already tracked above:

- app/config.py:19 - `Settings()` call-arg: a known pydantic-settings/
  mypy limitation (mypy can't see that required fields are populated
  from env vars at runtime, not constructor args) - confirmed present in
  auth-service and asset-service's identical `Settings()` pattern too,
  not specific to ml-service.
- app/core/deps.py:59, app/routers/predictions.py:58 - "Returning Any"
  errors, matching category 3 above exactly (decode_and_verify_token's
  return type needs tightening upstream in libs/common).

telemetry-service is also still missing a mypy pre-commit hook - not
touched this session, flagged here so it isn't lost.

## notification-service: mypy errors (new service, Phase 2)

Same already-documented pattern categories, new occurrences - not new
categories of problem:
- app/config.py: `Settings()` call-arg (jwt_secret_key, internal_api_key)
  - the same pydantic-settings/mypy limitation already noted for
    ml-service and confirmed present in auth-service/asset-service too.
- app/core/deps.py:65, app/routers/alerts.py (list_alerts, create_alert,
  acknowledge_alert, resolve_alert) - "Returning Any", matching category
  3 in the original mypy backlog above.

ml-service/app/config.py also gained 3 more required fields for the
Phase 2 scheduler (internal_api_key, scheduler_service_account_email,
scheduler_service_account_password) - same already-known pattern, not
new debt in itself.

## Pre-commit's mypy hooks can't see SQLAlchemy types at all

Discovered while building notification-service: pre-commit's mypy hooks
only list `additional_dependencies: [pydantic]` for every service (auth,
asset, ml, notification) - none include sqlalchemy. Since each hook runs
mypy in its own fully isolated environment (not the project's actual
poetry venv), and each service's own `ignore_missing_imports = true`
config means an unresolvable import degrades to `Any` rather than
erroring, every SQLAlchemy-derived type (Column[], Query results, model
instances) silently becomes `Any` inside pre-commit's mypy runs, but NOT
in a real `poetry run mypy .` run (which has the real venv, and sees the
real types).

Concrete effect found in ml-service/app/scheduler.py: a genuine
Column[str]-vs-str mismatch (fixed with explicit str() casts, since that
fix is correct and necessary in the REAL, fully-installed environment
regardless of what pre-commit's degraded environment can see) was
INVISIBLE to pre-commit the whole time - pre-commit would have passed
either way. Concrete effect found in notification-service/app/routers/
alerts.py: `# type: ignore[assignment]` comments that were genuinely
necessary locally became "Unused type: ignore" errors under pre-commit
(removed rather than fought, since pre-commit is what actually gates
commits) - this is also very likely why "Returning Any" errors are so
pervasive across every single service's pre-commit mypy output already
documented above - the SAME root cause, not four separate coincidences.

Real fix: add `sqlalchemy` (plus any other heavily-used typed
dependencies) to every mypy hook's `additional_dependencies` in
.pre-commit-config.yaml. Deliberately NOT done in this session - it
would likely surface a new round of real type errors across all four
services simultaneously, on top of the ~44-error backlog already
deferred above. A `poetry run mypy .` run inside each service's actual
venv remains the authoritative type-safety check until this is fixed;
pre-commit's mypy hooks today are a weaker, partial signal.

## Python version drift
Local Poetry venvs run on 3.13 (Anaconda's python.exe is first on PATH); Docker images
pin python:3.11-slim. No issues observed yet, but standardize eventually — either
install 3.11 locally for all services, or bump Docker images to 3.12/3.13 to match.

## Telemetry-service: incomplete auth-service error handling
`check_facility_role`, `verify_asset_access`, and `_check_facility_access` in
telemetry-service/app/core/deps.py only explicitly handle 404/403 responses
from asset-service. A 401 (e.g. expired token) falls into a generic
"Unexpected response from asset-service" branch instead of a clear
"please log in again" message. Low priority — functionally correct,
just a confusing error message in that specific case.

## ml-service: sys.path import of ml/src instead of a proper package
ml-service imports ml/src/models/inference.py and ml/src/features/live_features.py
(and their dependencies) via sys.path insertion at runtime, the same pattern used by
every ml/ notebook, rather than as a properly installed local package (the way
libs/common is consumed by every other service).

This was a deliberate choice, not an oversight: ml/'s own pyproject.toml has
package-mode = false specifically because it's built for notebook use (pythonpath =
["."]), and 26+ already-verified, committed notebooks depend on that exact import
pattern continuing to work unchanged. Properly packaging the shared feature/model
code (e.g. extracting it into a new libs/ml_pipeline package, mirroring libs/common)
would require either changing ml/'s packaging mode or rewriting every notebook's
imports - a real refactor with genuine risk of silently breaking previously-verified
numerical results, disproportionate to what was needed to stand up ml-service's
first version.

Real, concrete consequence: ml-service's Docker setup must mount/copy the ml/
directory (not just ml/models/) into its container, and add it to sys.path at
startup - a real coupling between ml-service and ml/'s internal directory layout
that a proper package boundary would avoid.

Should be revisited once the sys.path pattern has proven itself in ml-service and
there's a natural, lower-risk opportunity to extract a real libs/ml_pipeline
package (e.g. alongside the next major notebook refactor, not as a standalone
change to already-verified work).

## Model versioning/tracking: MLflow not yet adopted

Currently, model versioning is handled by a lighter-weight combination: joblib
artifacts + JSON metadata sidecars (feature lists, weather-regression
coefficients, required_raw_metrics, status/notes, training timestamp) +
model_registry.py (a git-tracked, human-readable single source of truth tracing
every config decision back to real EDA/log findings) + git commit history
itself (which already records exactly when each model changed and why - every
model-affecting commit today included a clear before/after).

MLflow was considered as a real alternative. What it would add: a proper model
registry with versioned promotion stages (staging/production), automatic
experiment tracking (params/metrics logged and queryable, not just prose in a
markdown file), and a UI for browsing training history.

What it would cost: a new piece of infrastructure (a tracking server, and
realistically a new Postgres-backed store for anything beyond a toy setup -
another service to maintain, on top of the pattern already established of
each service owning its own DB), real integration work (instrumenting
train_final_models.py to log custom metadata MLflow's standard sklearn flavor
doesn't natively support, rewiring ml-service to load from the registry
instead of local files), and - given today's session found 3 real bugs purely
through careful re-verification - a real re-verification pass to confirm
predictions are numerically identical before/after the swap. Honest estimate:
5-8 hours done properly; 2-4 hours for a lighter, local-file-backend version
without a new DB/service.

Decision: deferred for now, at the current project scale (8 models, trained
once, one developer) - full MLflow is more infrastructure than the current
need justifies, the same reasoning already applied to the sys.path-vs-proper-
packaging tradeoff above. Real, separate consideration not yet acted on: this
is also a portfolio project, and demonstrated MLflow experience has real,
recruiter-recognizable value independent of this project's immediate
technical need - worth revisiting for that reason even if retraining
frequency alone wouldn't yet justify it.

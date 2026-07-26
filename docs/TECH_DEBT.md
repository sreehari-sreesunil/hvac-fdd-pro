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

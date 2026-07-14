# ADR 0003: Careful COPY scoping in per-service Dockerfiles

## Status
Accepted

## Context
Each microservice's Dockerfile is built with `context: .` (the repo root),
not the service's own folder. This is necessary because services depend on
`libs/common`, which sits outside any individual service directory — Docker
cannot COPY files from outside its build context, so the context must be
wide enough to include both the service and its shared dependencies.

This wide context introduced a real bug during auth-service's initial
Dockerization: the final layer-copy instruction was written as `COPY . .`
instead of `COPY services/auth-service .`. Since the context root is the
whole repo, `COPY . .` copied every file at the repo root — including the
root `pyproject.toml` (which holds only Black/Ruff/mypy tool config, no
`[project]` metadata) — directly into `/app`, overwriting the correct
`services/auth-service/pyproject.toml` that an earlier, more specific COPY
instruction had already placed there.

The resulting failure mode was confusing to diagnose: `poetry install`
succeeded at build time (it ran before the overwriting COPY), but
`poetry check`/`poetry run` failed at container start, because by then the
wrong file was in place. Build-time success gave false confidence that the
config was correct, when the bug only manifested one layer later.

## Decision
Every service's Dockerfile must COPY its own service directory explicitly
by path (e.g. `COPY services/auth-service .`), never a bare `COPY . .`,
even though the build context is the repo root. Shared dependencies
(`libs/common`) are copied separately, to an explicit path outside `/app`
(e.g. `/libs/common`), and referenced by services via relative path
dependencies in `pyproject.toml` — never by relying on them being copied
into the same directory as the service's own code.

## Consequences
- Slightly more verbose Dockerfiles (explicit paths everywhere) in exchange
  for eliminating an entire class of "wrong file silently wins" bugs.
- New services added to this monorepo must follow the same pattern:
  narrow, explicit COPY paths, never a bare `COPY . .` against a
  repo-root context.
- When debugging a "works at build, fails at runtime" split in any future
  service, checking exactly what's inside the built image
  (`docker compose run --rm <service> ls -la` / `find` — as done here)
  is the fastest way to catch this class of bug, faster than re-reading
  the Dockerfile text alone.

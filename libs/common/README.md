# common

Shared utilities used by every microservice in the HVAC platform.

## What belongs here
Code that is genuinely identical across services: JWT verification, logging
setup, base exception types, shared response schemas.

## What does NOT belong here
Business logic, database models, or anything specific to one service's domain.
If only one service would ever import it, it belongs in that service, not here.

## Modules
- `security.py` — JWT token verification (verification only; auth-service is
  the sole issuer of tokens)
- `logging_config.py` — structured logging setup, call `configure_logging()`
  once at each service's startup
- `exceptions.py` — standard exception types (`NotFoundError`,
  `PermissionDeniedError`, `UnauthorizedError`) for consistent API error shapes
- `schemas.py` — shared Pydantic models, currently `ErrorResponse`

## Usage from another service
Add as a local path dependency in that service's `pyproject.toml`:
\`\`\`toml
common = {path = "../../libs/common", develop = true}
\`\`\`

## Running tests
\`\`\`bash
poetry install
poetry run pytest
\`\`\`

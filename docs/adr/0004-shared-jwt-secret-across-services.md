# ADR 0004: Shared JWT secret key across all services

## Status
Accepted

## Context
Only auth-service issues JWTs (see app/core/security.py in auth-service).
Every other service — starting with asset-service — verifies those tokens
using common.security.decode_and_verify_token, rather than owning any
token-issuing logic itself.

JWT signature verification requires the verifying service to use the exact
same secret key that the issuing service used to sign the token. If the
keys differ, even by one character, every token auth-service issues will
fail verification everywhere else — decode_and_verify_token returns None,
and every downstream request is rejected as unauthorized, with no error
message pointing at the actual cause (the failure looks identical to an
expired or genuinely invalid token).

This was encountered directly while wiring up asset-service: it required
its own separate .env file (each service manages its own environment
configuration independently), and the JWT_SECRET_KEY value in that file
must match auth-service's exactly, not just be "any long random string"
as was sufficient advice for auth-service's own initial setup.

## Decision
JWT_SECRET_KEY is treated as a single shared secret across the entire
platform, not a per-service value. Every service's .env file must contain
the identical value. This will be documented explicitly in each service's
README and .env.example, and — before any real deployment — this secret
will move to a proper shared secrets manager (see Week 9/10 security
hardening) rather than being copy-pasted across .env files by hand.

## Consequences
- Local development requires manually copying the same secret into every
  new service's .env file — an easy step to forget, and a likely source
  of confusing "valid-looking but rejected" auth failures for any new
  service added to this platform.
- In production, this becomes a genuine secrets-management requirement:
  rotating the JWT secret means coordinating the change across every
  service simultaneously, not just one. This is a real operational
  constraint worth designing around before going further than local dev
  (e.g. a shared secrets store like AWS Secrets Manager or Docker secrets,
  rather than per-service .env files, once this moves toward deployment).
- An alternative architecture (asymmetric signing — auth-service holds a
  private key, other services only need the corresponding public key to
  verify) would remove the "same secret everywhere" requirement entirely
  and is worth revisiting if secret-rotation coordination becomes painful.
  Not adopted now, to keep local development simple during active
  development.

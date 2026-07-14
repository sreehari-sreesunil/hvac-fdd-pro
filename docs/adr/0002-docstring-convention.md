# ADR 0002: Google-style docstrings

## Status
Accepted

## Context
Company-standard code requires consistent, readable documentation. Multiple
docstring conventions exist (Google, NumPy, reST); picking one avoids
inconsistency across services as the number of services and contributors grows.

## Decision
All modules, public functions, and classes use Google-style docstrings —
a one-line summary, followed by `Args`, `Returns`, and `Raises` sections
where relevant. Inline `#` comments are reserved for non-obvious *why*
(e.g. a deliberate security tradeoff, a workaround for a library quirk),
not for restating *what* the code already says.

## Consequences
- Consistent to read across all services, regardless of which service a new
  contributor opens first.
- Compatible with common auto-doc generation tools (e.g. Sphinx, mkdocs)
  if API documentation generation is added later.
- Slightly more upfront writing per function, in exchange for not having to
  re-derive intent from scratch when revisiting code months later.

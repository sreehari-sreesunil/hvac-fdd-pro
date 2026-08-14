from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.limiter import limiter
from app.db.session import Base, engine
from app.models import user  # noqa: F401
from app.routers import auth, organizations
from common.logging_config import configure_logging

configure_logging("auth-service")

app = FastAPI(title="auth-service", version="0.1.0")

# In-process rate limiting, not Redis-backed - this service runs as a
# single process/container with no horizontal scaling, same reasoning
# already established for ml-service's model cache (a shared external
# store only matters once there's a second instance that needs to see
# the same counters). Real, honest limitation worth stating: this means
# rate-limit state resets on every service restart, and would NOT be
# shared correctly across multiple replicas if this service is ever
# scaled horizontally - acceptable for this project's current single-
# instance scope, not a permanent architectural choice.
#
# Keyed by client IP (get_remote_address) - the standard default for
# public, pre-authentication endpoints like login/signup, where there's
# no user identity yet to key on. Real, honest limitation: this shares
# one bucket across everyone behind the same NAT/corporate network, and
# a motivated attacker can trivially defeat IP-based limiting with
# distributed source IPs - this raises the bar against casual/scripted
# brute-forcing, it is not a complete defense on its own.
app.state.limiter = limiter
# slowapi's own handler is typed for the narrower RateLimitExceeded, not
# Starlette's generic Exception - a known upstream slowapi/Starlette typing
# mismatch (Starlette's add_exception_handler wants a handler that accepts
# any Exception), not a bug in this code; the handler is correct at runtime.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "auth-service"}


app.include_router(auth.router)
app.include_router(organizations.router)

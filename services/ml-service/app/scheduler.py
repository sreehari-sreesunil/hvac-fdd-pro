"""Baseline-deviation alert scheduler.

Runs score_baseline() (the exact same function GET /baselines/{asset_id}
uses - see app/routers/baselines.py's module docstring) periodically for
every asset+metric that already has a fitted baseline, and pushes an
alert to notification-service when one deviates.

Deliberately scoped to baseline-deviation only for now, not
classifier/gatekeeper predictions - those need a "which model applies to
which asset" decision that predictions.py's own docstring already
flags as deliberately not automatic. Wiring them into this scheduler
later just means adding another _check_* function alongside this one;
notification-service's alert API is a generic sink and doesn't need to
change (see services/notification-service/app/models/alert.py).

Runs as a plain sync function (asyncio.run() internally) under
APScheduler's BackgroundScheduler, which executes jobs in a separate
thread - this avoids sharing FastAPI's own event loop, so a slow or
stuck scheduler run can't block request handling.
"""

import asyncio
import logging

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.db.session import SessionLocal
from app.models.asset_baseline import AssetBaseline
from app.routers.baselines import score_baseline

logger = logging.getLogger("ml-service.scheduler")

# is_deviation already means |z_score| > k_std; "critical" is reserved
# for readings far past that line, not just barely over it.
CRITICAL_Z_SCORE_MULTIPLE = 2.0


async def _get_service_account_token() -> str:
    """Log in fresh each run, rather than caching - baseline checks run
    at most every few minutes (scheduler_interval_seconds), well within
    normal JWT lifetimes, so token-refresh complexity isn't worth adding
    yet. Revisit if the interval ever needs to drop below a few minutes."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.auth_service_url}/auth/login",
            json={
                "email": settings.scheduler_service_account_email,
                "password": settings.scheduler_service_account_password,
            },
        )
        resp.raise_for_status()
        token: str = resp.json()["access_token"]
        return token


async def _has_open_alert(asset_id: str, token: str) -> bool:
    """Check for an existing OPEN baseline_deviation alert before creating
    another - without this, an ongoing deviation would get a brand new
    alert every single scheduler interval (a textbook alert-fatigue
    anti-pattern: real alerting systems like Prometheus Alertmanager
    de-duplicate an already-firing condition, they don't renotify every
    scrape). One alert stays open until a human (or a future
    auto-resolve rule) resolves it; only then can a new one be raised."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.notification_service_url}/alerts/{asset_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"status": "open"},
        )
        resp.raise_for_status()
        alerts = resp.json()
        return any(a["source"] == "baseline_deviation" for a in alerts)


async def _create_alert(
    asset_id: str, metric_definition_id: str, z_score: float, k_std: float, token: str
) -> bool:
    """Returns True if an alert was actually created, False if skipped
    (an open one already exists) - the caller logs accordingly rather
    than assuming success."""
    if await _has_open_alert(asset_id, token):
        return False

    severity = "critical" if abs(z_score) >= CRITICAL_Z_SCORE_MULTIPLE * k_std else "warning"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.notification_service_url}/alerts",
            headers={"X-Internal-Api-Key": settings.internal_api_key},
            json={
                "asset_id": asset_id,
                "metric_definition_id": metric_definition_id,
                "source": "baseline_deviation",
                "severity": severity,
                "message": (
                    f"Reading deviated {abs(z_score):.2f} standard deviations "
                    f"from its fitted per-asset baseline"
                ),
                "details": {"z_score": z_score, "k_std": k_std},
            },
        )
        resp.raise_for_status()
        return True


async def _check_all_baselines() -> None:
    db = SessionLocal()
    try:
        token = await _get_service_account_token()
        baselines = db.query(AssetBaseline).all()
        logger.info("Baseline check starting: %d fitted baseline(s) to evaluate", len(baselines))

        for baseline in baselines:
            # str(...) here isn't a defensive no-op - baseline.asset_id is
            # already a real Python str at RUNTIME (SQLAlchemy resolves
            # instance attributes to plain values), but mypy's static
            # view of an older-style declarative Column() sees
            # Column[str], not str, without a SQLAlchemy-aware plugin.
            # This is a known, common SQLAlchemy+mypy friction point, not
            # a real bug - see docs/TECH_DEBT.md.
            asset_id = str(baseline.asset_id)
            metric_definition_id = str(baseline.metric_definition_id)
            try:
                result = await score_baseline(asset_id, metric_definition_id, token, db)
                if result is None:
                    continue
                if result["is_deviation"]:
                    created = await _create_alert(
                        asset_id,
                        metric_definition_id,
                        result["z_score"],
                        result.get("k_std", 3.0),
                        token,
                    )
                    if created:
                        logger.warning(
                            "Alert created: asset=%s metric=%s z_score=%.2f",
                            baseline.asset_id,
                            baseline.metric_definition_id,
                            result["z_score"],
                        )
                    else:
                        logger.info(
                            "Skipped: asset=%s metric=%s already has an open "
                            "baseline_deviation alert (z_score=%.2f)",
                            baseline.asset_id,
                            baseline.metric_definition_id,
                            result["z_score"],
                        )
            except Exception:
                # One asset's failure (e.g. a telemetry gap) must not
                # stop every other asset from being checked.
                logger.exception(
                    "Baseline check failed for asset=%s metric=%s",
                    baseline.asset_id,
                    baseline.metric_definition_id,
                )
    finally:
        db.close()


def run_baseline_alert_check() -> None:
    """Entry point APScheduler calls - wraps the async work in its own
    event loop, since BackgroundScheduler's jobs run in a plain thread,
    not inside FastAPI's own event loop."""
    asyncio.run(_check_all_baselines())


scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    # Fires immediately on startup, then every scheduler_interval_seconds
    # after - a standard, simple pattern for interval jobs. (An earlier
    # version tried next_run_time=None to delay the first run, but that
    # appears to pause the job indefinitely rather than defer it by one
    # interval - a real bug, not a config choice; fixed by removing it.)
    scheduler.add_job(
        run_baseline_alert_check,
        "interval",
        seconds=settings.scheduler_interval_seconds,
        id="baseline_alert_check",
    )
    scheduler.start()
    logger.info(
        "Baseline alert scheduler started, interval=%ds", settings.scheduler_interval_seconds
    )


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)

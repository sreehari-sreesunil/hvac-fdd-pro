"""Basic load test for ml-service's prediction endpoints.

Targets the two real, live-verified prediction endpoints:
  - GET /predictions/{asset_id}?model_name=X          (single classifier)
  - GET /predictions/{asset_id}/attribute?model_names=...  (argmax across
    4 classifiers - the heavier, real-world path that copilot-service's
    diagnose_fault tool actually calls)

Weighted 3:1 toward /attribute, since that's the realistic heavy usage
pattern, not an arbitrary choice - a facilities manager asking the
copilot to diagnose a fault triggers exactly this endpoint.

Auth: logs in ONCE for the whole test run (see _get_shared_token()
below) and every simulated user shares that same token, rather than
each user logging in individually. This is a deliberate isolation
choice, not a shortcut: auth-service's real login rate limit
(5/minute per IP - see the rate-limiting work elsewhere in this
project) is a genuine, working security feature, but it means N
simulated users all logging in within a few seconds of each other at
test start would mostly get 429'd before ever reaching ml-service,
contaminating the results of a test that's specifically about
ml-service, not auth-service. A real client application (this
project's own frontend) authenticates once and reuses the token for
its whole session too, via refresh-on-401 - this mirrors that.
JWT access tokens are valid for 30 minutes (see
auth-service/app/config.py); the shared token is refreshed
automatically if a request comes back 401.

Usage:
    poetry run locust -f locustfile.py --host http://localhost:8003

Then open http://localhost:8089 to configure user count, spawn rate,
and start the run. Auth requests go to AUTH_SERVICE_URL directly
(auth-service isn't the system under test here, ml-service is), so
--host only needs to point at ml-service.
"""

import random
import threading

import requests
from locust import HttpUser, between, task

# Real test credentials/IDs, matching every other live verification
# done throughout this project (see docs/ and the project handoff -
# "ML Test Org" / "ML-Test-RTU-Full", the asset with ~18,000 real
# ingested LBNL telemetry readings across all 11 metrics needed by
# all 8 trained models).
AUTH_SERVICE_URL = "http://localhost:8000"
TEST_EMAIL = "mltest@example.com"
TEST_PASSWORD = "MLTestPass123"
ASSET_ID = "aaa87d18-b413-4628-aba8-1745feac3d59"

# All 4 "Usable"/"Usable with caveat" classifiers that fire on this
# asset's real condenser_fouling test data (see
# ml/TWO_STAGE_ARCHITECTURE_VALIDATION_LOG.md) - the exact same set
# used in this project's own live-verification of the argmax
# attribution endpoint.
ATTRIBUTION_MODELS = [
    "simulated_condenser_fouling",
    "simulated_overcharge",
    "simulated_liquidline_restriction",
    "simulated_suctionline_restriction",
]


_token_lock = threading.Lock()
_shared_token: str | None = None


def _get_shared_token(force_refresh: bool = False) -> str:
    """Log in once and cache the token for every simulated user to
    share, rather than each user hitting auth-service's real login
    rate limit (5/minute) individually - see the module docstring for
    why this isolation matters. Uses plain `requests`, not Locust's
    self.client, since this call is against auth-service and isn't
    itself part of what we're measuring (it wouldn't be tracked
    against the ml-service --host stats correctly anyway).

    Thread-safe: Locust runs each simulated user in its own greenlet,
    and multiple could call this at once on the first request or after
    a 401 - the lock ensures only one real login call happens even if
    several users hit this simultaneously.
    """
    global _shared_token
    with _token_lock:
        if _shared_token is not None and not force_refresh:
            return _shared_token
        response = requests.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=10,
        )
        response.raise_for_status()
        _shared_token = response.json()["access_token"]
        return _shared_token


class MlServiceUser(HttpUser):
    # 1-3s between a simulated user's requests - approximates a real
    # facilities manager clicking around a dashboard, not a tight
    # request-flood loop (which would test something closer to a DoS
    # scenario than realistic usage).
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.headers = {"Authorization": f"Bearer {_get_shared_token()}"}

    def _refresh_token(self) -> None:
        self.headers = {"Authorization": f"Bearer {_get_shared_token(force_refresh=True)}"}

    @task(3)
    def attribute_fault(self) -> None:
        """The heavier, real-world path - runs 4 classifiers per
        request, argmax's the result. What diagnose_fault actually
        calls."""
        params = "&".join(f"model_names={m}" for m in ATTRIBUTION_MODELS)
        with self.client.get(
            f"/predictions/{ASSET_ID}/attribute?{params}",
            headers=self.headers,
            name="/predictions/{asset_id}/attribute",
            catch_response=True,
        ) as response:
            if response.status_code == 401:
                self._refresh_token()
                response.failure("token expired, refreshed")
            elif response.status_code != 200:
                response.failure(f"unexpected status {response.status_code}")

    @task(1)
    def single_prediction(self) -> None:
        """The lighter path - one classifier per request."""
        model_name = random.choice(ATTRIBUTION_MODELS)
        with self.client.get(
            f"/predictions/{ASSET_ID}?model_name={model_name}",
            headers=self.headers,
            name="/predictions/{asset_id}",
            catch_response=True,
        ) as response:
            if response.status_code == 401:
                self._refresh_token()
                response.failure("token expired, refreshed")
            elif response.status_code != 200:
                response.failure(f"unexpected status {response.status_code}")

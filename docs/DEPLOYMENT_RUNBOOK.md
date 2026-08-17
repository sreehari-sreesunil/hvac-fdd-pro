# Deployment Runbook

Real, evidence-based deployment steps - written from an actual live
deployment (GCP Compute Engine, `plenumcontrol.in`), including the
real gotchas hit along the way, not a theoretical guide.

## Architecture

Single VM, Docker Compose, Caddy as reverse proxy + automatic TLS.
One subdomain per backend service (matches the frontend's existing
per-service `NEXT_PUBLIC_*_SERVICE_URL` env var shape - no unified
API gateway path, no frontend code changes needed beyond new URL
values):

- `plenumcontrol.in` / `www.plenumcontrol.in` → frontend
- `auth.plenumcontrol.in` → auth-service
- `asset.plenumcontrol.in` → asset-service
- `telemetry.plenumcontrol.in` → telemetry-service
- `ml.plenumcontrol.in` → ml-service
- `notification.plenumcontrol.in` → notification-service
- `copilot.plenumcontrol.in` → copilot-service

Chosen over AWS ECS/Fargate deliberately: a single-VM Docker Compose
deployment is dramatically faster and lower-risk for a first cloud
deployment, while still being genuinely real production infrastructure
(reverse proxy + TLS, environment/secrets management, process
supervision) - not a toy setup. See project decision log for the full
tradeoff reasoning.

## Prerequisites

- A domain, with DNS access (A records need to point at the server).
- A VM: minimum 2 vCPU / 4GB RAM (`e2-medium` on GCP, `t3.medium` on
  AWS) and **at least 30GB disk** - see the disk-space gotcha below,
  30GB is a real minimum, not generous headroom.
- Docker + Docker Compose installed on the VM (`curl -fsSL
  https://get.docker.com | sh`, then `sudo usermod -aG docker $USER`
  and reconnect the SSH session for group membership to take effect).

## DNS

Add an A record for the root domain, `www`, and every backend
subdomain above, all pointing at the VM's public IP. Verify propagation
before starting Caddy - it needs working DNS to complete Let's
Encrypt's HTTP-01 challenge:

```bash
for sub in "" auth. asset. telemetry. ml. notification. copilot.; do
  echo -n "${sub}yourdomain.com -> "
  dig +short "${sub}yourdomain.com" @8.8.8.8
done
```

Every line should show the VM's real IP before proceeding.

## Secrets (.env, server-side only, never committed)

```bash
git clone <repo-url>
cd hvac-fdd-pro
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env
echo "INTERNAL_API_KEY=$(openssl rand -base64 32)" >> .env
echo "SCHEDULER_SERVICE_ACCOUNT_PASSWORD=$(openssl rand -base64 24)" >> .env
echo "GROQ_API_KEY=<your real key>" >> .env
echo "CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com" >> .env
```

**Real gotcha #1 - the scheduler account password.** ml-service's
background scheduler logs in as a real user
(`ml-scheduler-service@hvacfddpro.com` by default) to authenticate its
own internal API calls. On a **fresh** database, that user doesn't
exist yet, so this isn't an issue for a first deployment - the
scheduler will simply have no matching account until one is created.
This only matters when **rotating** the password on an
**already-running** deployment: changing the env var alone doesn't
update the real stored password hash for that account, and the
scheduler's login will start failing with 401 until the account's
actual hash is updated to match (see the project's commit history for
the exact procedure using `hash_password()` + a direct `UPDATE`).

**Real gotcha #2 - CORS.** `CORS_ALLOWED_ORIGINS` defaults to
`http://localhost:3000` if not set. Forgetting this line above means
the browser will silently succeed against `curl` (which doesn't
enforce CORS) while every real browser request fails with a CORS
preflight error - `curl` working is not proof the frontend works.
Confirmed as a real, live issue on the actual first deployment; caught
via the browser console's CORS error message, not assumed.

## Build and start

Build **one service at a time**, not all at once:

```bash
docker compose build auth-service asset-service telemetry-service notification-service
docker compose build ml-service
docker compose build copilot-service
docker compose build frontend
docker compose up -d
```

**Real gotcha #3 - disk space.** Building all 8 images in parallel
(the default `docker compose up -d --build` behavior) can spike peak
disk usage well beyond any single image's final size, since multiple
large image layers extract simultaneously. On a 30GB disk, this
genuinely failed with "no space left on device" when building in
parallel, but succeeded building sequentially. `docker system df` and
`docker system prune -af` are the real, useful commands for diagnosing
and recovering from this if it happens - a build failure doesn't
always mean the filesystem itself is actually full at rest, a failed
build can leave several GB of orphaned intermediate layers behind.

**Real gotcha #4 - torch's CUDA build.** `copilot-service` depends on
`sentence-transformers`, which pulls in `torch`. PyPI's default Linux
wheel for `torch` is the full CUDA-enabled build (several GB of GPU
libraries), which is pure waste on a VM with no GPU - large enough on
its own to fill an entire 30GB disk. Fixed by pinning `torch` to
PyTorch's own official CPU-only wheel index
(`download.pytorch.org/whl/cpu`) via an explicit Poetry source - see
`services/copilot-service/pyproject.toml`. Already fixed in this
repo; noted here in case a future dependency reintroduces a
GPU-flavored package without the same explicit pin.

## Verification

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://yourdomain.com
for sub in auth asset telemetry ml notification copilot; do
  echo -n "${sub}.yourdomain.com/health -> "
  curl -s -o /dev/null -w "%{http_code}\n" https://${sub}.yourdomain.com/health
done
```

Every line should show `200`. Then do a real, live signup through the
actual browser (not just curl) - this is what actually caught the
CORS gotcha above, since curl doesn't enforce the same-origin policy
a real browser does.

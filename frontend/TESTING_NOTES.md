# Testing notes

## Running locally against the three backend services

From the repo root:

```bash
docker compose up -d postgres mosquitto auth-service asset-service telemetry-service
```

Wait until `docker compose ps` shows `auth-service` and `asset-service` as
`healthy` (telemetry-service has no healthcheck defined but comes up once
the other two are healthy). Services listen on:

- auth-service: `http://localhost:8000`
- asset-service: `http://localhost:8001`
- telemetry-service: `http://localhost:8002`

Then, from `frontend/`:

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

The app runs on `http://localhost:3000`. `.env.local.example` already points
at the three ports above — no edits needed for local dev.

## Known gap (backend, not this frontend's scope)

`telemetry-service` has no `GET /edge-devices` list endpoint, so the
facility detail page can only show edge devices created earlier **in the
current browser session** — devices from a previous session won't reappear
after a refresh. This is a backend gap, not a frontend bug; flagged rather
than worked around.

## Manual test checklist

- [ ] **Signup → org → facility → asset → dashboard**: sign up, you land in
      the onboarding wizard; create an organization, a facility, and an
      asset (creating a new asset type inline works too). Each step shows
      an "X added" confirmation. You land on `/dashboard` and see the new
      asset as a card.
- [ ] **Light/dark toggle actually changes colors**: toggle dark mode from
      Settings or the top bar. Background, surface, and text colors change
      on the dashboard. Visit `/` (marketing) or `/copilot` — both stay
      dark regardless of the dashboard's saved preference.
- [ ] **Unit toggle actually converts values**: on an asset with a mapped
      temperature reading, toggle metric units in Settings — the displayed
      value and unit suffix (°F ↔ °C) both change, and the choice survives
      a page reload (persisted to localStorage).
- [ ] **Stale asset**: an asset whose most recent reading is 2–15 minutes
      old shows the amber "Stale · last updated Xm ago" state — muted, not
      styled as an error.
- [ ] **Simulated disconnected state**: append `?simulateReliability=live`,
      `?simulateReliability=stale`, or `?simulateReliability=disconnected`
      to a dashboard/asset-detail URL (dev builds only) to force each of
      the three reliability states and confirm they're visually and
      semantically distinct — Disconnected reads "Awaiting localized
      heartbeat" and is deliberately calm, not red/alarm-styled.
- [ ] **Tablet-width sidebar collapse**: resize the window to ~768–1024px.
      The full labeled sidebar disappears and a 64px icon-only rail takes
      its place — the nav genuinely reflows, it doesn't just clip. Below
      768px, the rail also hides and a hamburger button opens a full
      slide-over drawer instead.
- [ ] **`prefers-reduced-motion` stops the schematic animation**: in
      DevTools, emulate `prefers-reduced-motion: reduce` (Rendering tab →
      "Emulate CSS media feature prefers-reduced-motion"), reload `/`. The
      traveling flow dots and pulsing sensor dots on the hero schematic
      stop; live-value roll/tick transitions elsewhere stop too. Severity
      color transitions (e.g. a card's badge changing tone) still happen —
      those are treated as essential feedback, not decoration.
- [ ] **Role gating**: a `viewer`-role org member cannot see the "Add
      device" form or "Issue key" buttons on a facility's detail page
      (checked against the `role` field from `GET /organizations`).
- [ ] **503 vs 403 vs 404 distinction**: stop `asset-service`
      (`docker compose stop asset-service`) and reload the dashboard,
      facilities list, a facility's detail page, or an asset's detail
      page — each shows a calm "temporarily unavailable" state with a
      Retry button (amber tone), never a blank page. Restart it afterward
      (`docker compose start asset-service`). Separately, visit a facility
      or asset detail URL with a made-up UUID — you get a distinct
      "doesn't exist or was removed" state (no Retry button, since
      retrying won't help). A `viewer` on a facility they're not a member
      of would see a third distinct "you don't have access" state — all
      three must be visually distinguishable at a glance, not just by
      reading the copy.
- [ ] **Keyboard navigation**: tab through the dashboard, forms, and
      modals — every interactive element (links, buttons, inputs, toggles)
      shows a visible focus ring.
- [ ] **Ingestion key one-time reveal**: from a facility's detail page, add
      a device and click "Issue key". The raw key is shown once with a
      "won't be shown again" warning; the "Done" button stays disabled
      until the acknowledgment checkbox is checked.
- [ ] **Metric mapping + backfill**: post a telemetry reading with an
      unrecognized `external_key` (e.g. via `curl` against
      `POST http://localhost:8002/telemetry` with a device's
      `X-Ingestion-Key`), confirm it shows up under "Unmapped keys" on the
      asset detail page, map it to a metric, and confirm the reading
      immediately appears under "Recent readings" with the metric's
      display name and unit.

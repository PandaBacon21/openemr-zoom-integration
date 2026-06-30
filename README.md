# Zoom / OpenEMR Integration

Lightweight Flask backend for linking Zoom account data with OpenEMR workflows.

Current implemented areas:

- Zoom account registration, update, and deregistration
- OpenEMR dynamic client registration + registration verification checks
- User mapping management (OpenEMR provider and/or ZCC agent <-> Zoom user)
- Appointment type filter management
- OpenEMR appointment webhook handling for create, update, and delete flows
- Meeting lifecycle handling (create/update/recreate/delete) with MeetingRecord persistence
- OpenEMR appointment URL writeback (`pc_website`) after meeting create/recreate
- Zoom waiting-room/meeting-start/meeting-end handling drives a forward-only appointment status state machine (Pending → Arrived → In Exam Room → Checked Out), keeping both `pc_apptstatus` and `patient_tracker_element` in sync so the calendar and the Flow Board agree
- Zoom clinical note retrieval/writeback, manual OpenEMR fetch proxy, and Zoom note completion triggered on eSign of a SOAP / Clinical Notes form or the encounter
- eSign-locked encounter guard refuses writeback (async webhook retries and manual fetch) and hides the OpenEMR Retrieve Zoom Note button on locked or non-Zoom-linked encounters
- Hydrate Demo Data endpoint + admin UI button — idempotent backfill of the next-2-weekdays × 2-slots-per-day grid with Zoom-typed appointments + real Zoom meetings, respecting per-account appointment-type filters
- Per-account Zoom webhook URL (`/webhooks/zoom/<account_id>`) so CRC URL validation resolves the correct secret and payload account_id is cross-checked against the path
- Audit logging for webhook intake, meeting lifecycle, note, completion, eSign-locked refusals, status transitions, hydration, and config events
- Paginated audit log API for the admin UI
- Per-account config records for timezone, clinical note writeback mode, demo patient contact overrides, and Epic-ZCC behavior/settings
- Zoom EHR Context auth and appointment lookup endpoints
- Epic-style ZCC CTI middleware, gated by `ENABLE_EPIC_ZCC`, including OAuth/JWKS, PatientLookUp, Practitioner.Search, ReceiveCommunication3 screen-pop dispatch, OpenEMR SSE screen-pop bootstrap, ZCC user lookup, and outbound click-to-dial plumbing with ZCC-agent-only OpenEMR controls
- OpenEMR listener patch module wiring for `AppointmentSetEvent` and `AppointmentDialogCloseEvent`
- OpenEMR provider + appointment type lookup helpers
- Zoom user lookup helper
- Protected admin/config endpoints via JWT bearer auth
- JWKS endpoint for per-account key usage

## Internal Developer Reference

- See [ARCHITECTURE.md](ARCHITECTURE.md) for the top-level system architecture: service topology, network segmentation, data flow sequences, env var inventory, persistent state, production hardening (DbGate gating, single-replica scheduler), and the Must / Should / Must-preserve summary for a Kubernetes deployment.
- See [docs/internal/integration-reference.md](docs/internal/integration-reference.md) for:
  - current data model field contracts
  - webhook payload/signature contract
  - OpenEMR appointment status code mapping notes
  - migration and test coverage pointers
- See [docs/internal/implementation-setup-guide.md](docs/internal/implementation-setup-guide.md) for the repo-based deployment/setup checklist and credential reference.
- See [docs/internal/phase-2-sprint-plan.md](docs/internal/phase-2-sprint-plan.md) for the Phase 2 Sprint 7-13 plan with implementation status per story.

## Usage

> **Note**
>
> The following sample application is a personal, open-source project shared by the app creator and not an officially supported Zoom Communications, Inc. sample application. Zoom Communications, Inc., its employees and affiliates are not responsible for the use and maintenance of this application.
>
> Please use this sample application for inspiration, exploration and experimentation at your own risk and enjoyment. You may reach out to the app creator and broader Zoom Developer community on https://devforum.zoom.us/ for technical discussion and assistance, but understand there is no service level agreement support for this application. Thank you and happy coding!

## Quick Start

The stack is Docker Compose orchestrated — a custom OpenEMR image built from `openemr/Dockerfile` (PHP/Apache, with all Zoomly patches + branding baked in), MariaDB, PostgreSQL, the Flask integration service (`zoom-bridge`), and the React admin UI all run as containers, along with a one-shot `zoom-module-init` container that registers the Zoom Appointment Listener module in the OpenEMR DB. **Do not run `python run.py` directly** — Flask alone has no functional database peers and OpenEMR isn't started.

### Prerequisites

- Docker + Docker Compose
- Node.js 20+ (only if you want Vite HMR for React development; the production bundle is baked into the Flask image)

### 1. Configure environment

```bash
cp .env.example .env
```

Set required values. The most load-bearing ones:

**Flask integration secrets**
- `ENCRYPTION_KEY` — AES key for encrypted-at-rest stored Zoom/OpenEMR credentials. **Do not rotate without using `server/scripts/rotate-encryption-key.py`** — every stored credential becomes unreadable otherwise.
- `SECRET_KEY`, `API_KEY` — Flask secrets
- `CONFIG_ADMIN_PASSWORD` — login password for the admin UI
- `CONFIG_JWT_SECRET` — signs admin UI JWTs
- `OPENEMR_FLASK_SECRET` — HMAC shared between OpenEMR and Flask for webhook signing (same value in both)

**OpenEMR MariaDB**
- `MYSQL_ROOT_PASSWORD`
- `OPENEMR_DB_USER`, `OPENEMR_DB_PASS`, `OPENEMR_DB_NAME` (= `openemr`)
- `OPENEMR_DB_HOST` (= `mariadb`), `OPENEMR_DB_PORT` (= `3306`)
- `OPENEMR_ADMIN_USER`, `OPENEMR_ADMIN_PASS` — initial OpenEMR admin login

**Zoomly Postgres**
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `DATABASE_URL` is constructed by `docker-compose.yml` for `zoom-bridge` from the `POSTGRES_*` values. Set it manually only for host-side/server-only runs outside Compose.

**URLs**
- `OPENEMR_BASE_URL` (= `http://openemr:80`) — internal HTTP, used by Flask
- `OPENEMR_FHIR_BASE_URL` (= `http://openemr:80/apis/default/fhir`)
- `OPENEMR_PUBLIC_URL` — public HTTPS URL of OpenEMR. **Used only for OAuth2 `aud` claims and outbound URLs to Zoom**; never used for container-to-container traffic.
- `APP_PUBLIC_URL` — public HTTPS URL of `zoom-bridge` (for webhook callbacks)
- `APP_INTERNAL_URL` (= `http://zoom-bridge:5000`)
- `OPENEMR_SCOPES` — space-delimited SMART scopes

**Feature flags and Epic-ZCC**
- `ENABLE_DBGATE` — set to `true` in dev/staging to enable the DbGate database browser proxied at `/admin/db`. Leave unset or `false` in production. See [ARCHITECTURE.md §13](ARCHITECTURE.md) for the three-layer gating model.
- `ENABLE_EPIC_ZCC` — set to `true` only when configuring Epic-style ZCC CTI demos. When false, Flask does not register the Epic-ZCC runtime blueprints and the React UI hides the Epic ZCC tab.
- `EPIC_ZCC_CLIENT_ID` — global client ID shown in the Epic ZCC config tab and expected by ZCC CTI auth when Epic-ZCC is enabled.
- `ZOOMLY_EPIC_ZCC_CLIENT_URL` — optional OpenEMR top-nav CTI iframe URL for the Epic-ZCC callbar shell. The OpenEMR callbar, SSE subscriber, and click-to-call phone links render only for logged-in users whose bootstrap request returns an active ZCC-agent stream.

See [docs/internal/implementation-setup-guide.md](docs/internal/implementation-setup-guide.md) for the full env-var reference (what each variable does, where to source it, and rollback semantics for registration secrets).

### 2. Start the stack

```bash
# Fresh clone: bootstrap the gitignored dev override from the committed template
cp docker-compose.override.yml.example docker-compose.override.yml

./server/scripts/start-dev.sh
```

This brings up all containers (using Compose `--profile non-prod` to include DbGate), waits for OpenEMR to be healthy (~3-5 min on first boot, longer on the very first build when the custom OpenEMR image is being layered), and waits for the one-shot module init to finish.

In default dev mode, Docker Compose auto-loads `docker-compose.override.yml` alongside the base file. The override carries (1) the Flask dev server (FLASK_DEBUG, hot reload, live `./server/app` mount) and (2) bind mounts of every file in `openemr/patches/` over the baked OpenEMR image. The bind mounts let you edit a `.php` file in `openemr/patches/`, refresh the page, and have mod_php pick up the change without rebuilding the image. The script's `chmod` block fixes ownership on bind-mounted files to match what OpenEMR expects (`apache:apache` + `644`).

To simulate staging/prod locally — running the baked OpenEMR image (`zoomly-openemr:local` from `openemr/Dockerfile`) with no patch shadowing and gunicorn instead of the Flask dev server — pass `--baked`:

```bash
./server/scripts/start-dev.sh --baked
```

This skips the override entirely (explicit `-f docker-compose.yml`) so you can confirm a patch change is actually baked into the image before deploying. After landing a patch edit, run `docker compose build openemr` to refresh the image, then `start-dev.sh --baked` to verify.

### 3. Run database migrations

```bash
docker exec zoom-bridge uv run alembic upgrade head
```

Migrations don't run automatically in dev. The staging and prod scripts (`start-staging.sh`, `start-prod.sh`) run them at the end of their boot sequences.

### 4. Seed demo data (recommended)

Without seed data, OpenEMR has no providers, patients, or appointments — most demo flows won't exercise correctly.

```bash
./seed_data/reset.sh && ./seed_data/seed.sh
```

Loads 7 ordered SQL files into a single MariaDB session (idempotent — re-runs produce the same state). See [docs/internal/implementation-setup-guide.md](docs/internal/implementation-setup-guide.md) §"Optional: seed OpenEMR demo data" for details.

Current seed shape: 4 facilities, 18 patient-panel providers, 108 patients (PIDs 100-207), 292 weekday appointments, regional pharmacies/payers, complete patient contact/insurance fields, and provider+nurse care teams.

### 5. (Optional) React development with HMR

The Flask container serves the production Vite build out of `server/app/static/`. For frontend development with hot-module-reload:

```bash
cd client
npm install        # first time only
npm run dev        # served at http://localhost:5173, proxies API to :5000
```

To pick up React changes in the Flask-served bundle without HMR, build into the static folder:

```bash
cd client && npm run build
```

### Local URLs

| URL | What it serves |
| --- | --- |
| `http://localhost:8300` | OpenEMR — clinical workflows, calendar, encounters |
| `http://localhost:5000` | Flask + React admin UI (production build) |
| `http://localhost:5173` | React dev server with HMR (only when running `npm run dev`) |

### Other useful entry points

```bash
# Staging dry-run on your local box — no dev overrides, gunicorn-gevent,
# baked image, same shape staging runs:
./server/scripts/start-staging.sh

# Production-shaped start — only docker-compose.yml, no overrides, no DbGate:
./server/scripts/start-prod.sh

# Rebuild the custom OpenEMR image after editing anything in openemr/patches/ or
# openemr/branding/ (locks the change in for staging/prod):
docker compose build openemr --no-cache

# Tear down (preserves volumes / DB data):
docker compose down

# Tear down + wipe all data volumes (clean slate):
docker compose down -v
```

## API Surface (Current)

Health and keys:

- `GET /health`
- `GET /.well-known/jwks.json`

Admin authentication:

- `POST /api/auth/login`
- `GET /api/auth/verify`

Configuration and registration (JWT bearer protected):

- `POST /config/register`
- `PATCH /config/register/<zoom_account_id>`
- `DELETE /config/register/<zoom_account_id>`
- `GET /config/registrations`
- `POST /config/register/<zoom_account_id>/verify`
- `POST /config/ehr-credentials`

Registration create/update responses include `tenant_id` for Zoom EHR Context and `note_writeback_mode` for clinical note writes. Supported writeback modes are `both`, `clinical_note_only`, and `soap_only`.

User/provider mapping management (JWT bearer protected):

- `POST /config/providers`
- `GET /config/providers?zoom_account_id=...`
- `DELETE /config/providers/<openemr_user_id>?zoom_account_id=...`

Appointment filter management (JWT bearer protected):

- `POST /config/appointment-types`
- `GET /config/appointment-types?zoom_account_id=...`
- `DELETE /config/appointment-types/<type_id>?zoom_account_id=...`

OpenEMR and Zoom lookup helpers (JWT bearer protected):

- `GET /openemr/providers?zoom_account_id=...`
- `GET /openemr/appointment-types?zoom_account_id=...`
- `GET /zoom/users?zoom_account_id=...`
- `GET /zoom/zcc/users?zoom_account_id=...`

Audit logs (JWT bearer protected):

- `GET /audit/logs?zoom_account_id=...&event_type=...&success=true&page=1&per_page=50`

Feature flags (JWT bearer protected):

- `GET /config/features` — returns process-wide UI feature gates (currently `{"db_browser": bool, "epic_zcc": bool}`) consumed by the React `FeaturesContext` to hide/show nav entries

Epic-ZCC configuration (JWT bearer protected, feature-gated in the UI):

- `GET /config/account/<zoom_account_id>/epic-zcc`
- `PATCH /config/account/<zoom_account_id>/epic-zcc`
- `POST /config/account/<zoom_account_id>/epic-zcc/initialize`

DbGate database browser proxy — **non-prod only** (JWT cookie protected, since iframes can't send custom auth headers). The blueprint is conditionally registered based on `ENABLE_DBGATE`; the DbGate container is gated behind the `non-prod` compose profile. In production both layers are off, so these routes return 404 and the upstream container isn't running:

- `GET/POST /admin/db`
- `GET/POST /admin/db/<path>`

Protected routes require:

```http
Authorization: Bearer <token-from-/api/auth/login>
```

OpenEMR-signed note endpoints:

- `POST /zoom/encounter/<encounter_number>/fetch_zoom_note` (signature required; JWT exempt; returns 409 if the encounter or its SOAP / Clinical Notes form is eSign-locked)
- `POST /zoom/encounter/<encounter_number>/complete_zoom_note` (signature required; JWT exempt; idempotent Zoom completion hook; every skip/error path audited)

Demo hydration (JWT bearer protected):

- `POST /config/demo/hydrate` — idempotent backfill of the next-2-weekdays × 2-slots-per-day appointment + Zoom meeting grid for every active provider-role user mapping on the account

Epic-ZCC CTI endpoints:

- Registered only when `ENABLE_EPIC_ZCC=true`
- External Zoom/Epic-shaped base: `/zoomly/<zoom_account_id>/interconnect-amcurprd-oauth`
- `POST /oauth2/token`
- `GET /oauth2/keys/1/<epic_kid>`
- `POST /api/epic/2012/EMPI/Patient/PATIENTLOOKUP/Lookup`
- `GET /api/FHIR/R4/Practitioner`
- `POST /api/epic/2023/Common/Utility/RECEIVECOMMUNICATION3/ReceiveCommunication3`
- `GET /screenpop/stream`
- `POST /cti/initiate-call`
- OpenEMR-facing bootstrap base: `/zoomly/epic-zcc`
- `POST /screenpop/bootstrap`

OpenEMR click-to-call controls are intentionally session-gated. Non-ZCC users see plain phone numbers and no callbar/subscriber assets. Demo seed phone numbers ending in `555-####` are also left unlinked so synthetic demo numbers are not dialed through ZCC.

Inbound webhook endpoints:

- `POST /webhooks/openemr` (`X-Zoomly-Signature` required)
- `POST /webhooks/zoom/<account_id>` (Zoom webhook signature flow — per-account path)

Zoom EHR Context endpoints:

- `GET /rest/auth/gettoken` (`Authorization: Basic ...` plus `X-Tenant-ID`)
- `POST /rest/openendpoint/service/getAppointments` (`Authorization: Bearer ...` plus `X-Tenant-ID`)

## Testing

The project pattern during development is to run pytest **inside the running container**:

```bash
docker exec zoom-bridge uv run pytest -q
```

This uses the container's installed deps and the same Python environment Flask runs against.

For host-side execution (e.g. CI, or quickly iterating without the stack up), use the wrapper script:

```bash
server/scripts/test.sh
```

This runs `uv run pytest -q` from the `server/` directory with `UV_CACHE_DIR` pinned to `server/.uv-cache` so it works in restricted/sandboxed environments. Requires `uv` installed on the host plus `uv sync --group dev` first.

Current test suite coverage includes auth/JWKS (endpoint hit audits, OpenEMR token refresh + verify outcomes, Zoom token refresh + credentials-validation outcomes), registration lifecycle and updates, account config migration contracts, user mappings, appointment filters, appointment event processing/webhooks (including the `appointment.deleted` preserve-vs-delete branch on `ClinicalNoteRecord` presence), audit logging and audit API filtering, EHR Context auth/appointment lookup, OpenEMR lookups/writeback, Epic-ZCC auth/PatientLookUp/Practitioner/ReceiveCommunication3/screen-pop/outbound/config flows, clinical note writeback mode routing, SOAP/Clinical Notes form upsert dedup (encounter-based), `MeetingRecord.clinical_note` ordering guarantees, manual `fetch_zoom_note` audit/log coverage, eSign-locked encounter writeback refusal (encounter-, SOAP-, and Clinical-Notes-level locks), forward-only appointment status state machine including the `patient_tracker_element` sync that keeps the Flow Board aligned, hydration service helpers and orchestrator, past locked-encounter seeder, demo seed/reset contracts, the `/config/features` feature-flag endpoint, Zoom lookups, protected blueprint endpoints, and migration contract checks.

Latest backend run result in this workspace: `474 passed`.

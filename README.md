# Zoom / OpenEMR Integration

Lightweight Flask backend for linking Zoom account data with OpenEMR workflows.

Current implemented areas:

- Zoom account registration, update, and deregistration
- OpenEMR dynamic client registration + registration verification checks
- Provider mapping management (OpenEMR provider <-> Zoom user)
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
- Per-account config records for timezone, shared Zoom user behavior, clinical note writeback mode, and demo patient contact overrides
- Zoom EHR Context auth and appointment lookup endpoints
- OpenEMR listener patch module wiring for `AppointmentSetEvent` and `AppointmentDialogCloseEvent`
- OpenEMR provider + appointment type lookup helpers
- Zoom user lookup helper
- Protected admin/config endpoints via JWT bearer auth
- JWKS endpoint for per-account key usage

## Internal Developer Reference

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

## Quick Start (Backend)

1. Copy environment defaults:

```bash
cp .env.example .env
```

2. Set required values in `.env` for your environment:

- `ENCRYPTION_KEY`
- `CONFIG_ADMIN_PASSWORD`
- `CONFIG_JWT_SECRET`
- `OPENEMR_BASE_URL`
- `OPENEMR_PUBLIC_URL`
- `OPENEMR_FHIR_BASE_URL`
- `OPENEMR_FLASK_SECRET`
- `OPENEMR_DB_USER`
- `OPENEMR_DB_PASS`
- `OPENEMR_DB_HOST`
- `OPENEMR_DB_PORT`
- `OPENEMR_DB_NAME`
- `APP_PUBLIC_URL`
- `APP_INTERNAL_URL`
- `OPENEMR_SCOPES` (space-delimited SMART scopes)

3. Install backend dependencies:

```bash
cd server
uv sync --group dev
```

4. Run the backend:

```bash
uv run python run.py
```

Default local URL: `http://localhost:5000`

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

Registration create/update responses include `tenant_id` for Zoom EHR Context and `note_writeback_mode` for clinical note writes. Supported writeback modes are `both`, `clinical_note_only`, and `soap_only`.

Provider mapping management (JWT bearer protected):

- `POST /config/providers`
- `GET /config/providers?zoom_account_id=...`
- `DELETE /config/providers/<openemr_provider_id>?zoom_account_id=...`

Appointment filter management (JWT bearer protected):

- `POST /config/appointment-types`
- `GET /config/appointment-types?zoom_account_id=...`
- `DELETE /config/appointment-types/<type_id>?zoom_account_id=...`

OpenEMR and Zoom lookup helpers (JWT bearer protected):

- `GET /openemr/providers?zoom_account_id=...`
- `GET /openemr/appointment-types?zoom_account_id=...`
- `GET /zoom/users?zoom_account_id=...`

Audit logs (JWT bearer protected):

- `GET /audit/logs?zoom_account_id=...&event_type=...&success=true&page=1&per_page=50`

DbGate database browser proxy (JWT cookie protected — required because iframes cannot send custom auth headers):

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

- `POST /config/demo/hydrate` — idempotent backfill of the next-2-weekdays × 2-slots-per-day appointment + Zoom meeting grid for every active provider mapping on the account

Inbound webhook endpoints:

- `POST /webhooks/openemr` (`X-Zoomly-Signature` required)
- `POST /webhooks/zoom/<account_id>` (Zoom webhook signature flow — per-account path)

Zoom EHR Context endpoints:

- `GET /rest/auth/gettoken` (`Authorization: Basic ...` plus `X-Tenant-ID`)
- `POST /rest/openendpoint/service/getAppointments` (`Authorization: Bearer ...` plus `X-Tenant-ID`)

## Testing

Run backend tests from the repository root:

```bash
server/scripts/test.sh
```

This script runs `uv run pytest -q` with `UV_CACHE_DIR` pinned to `server/.uv-cache` by default so it works in restricted/sandboxed environments.

Current test suite coverage includes auth/JWKS (endpoint hit audits, OpenEMR token refresh + verify outcomes, Zoom token refresh + credentials-validation outcomes), registration lifecycle and updates, account config migration contracts, provider mappings, appointment filters, appointment event processing/webhooks (including the `appointment.deleted` preserve-vs-delete branch on `ClinicalNoteRecord` presence), audit logging and audit API filtering, EHR Context auth/appointment lookup, OpenEMR lookups/writeback, clinical note writeback mode routing, SOAP/Clinical Notes form upsert dedup (encounter-based), `MeetingRecord.clinical_note` ordering guarantees, manual `fetch_zoom_note` audit/log coverage, eSign-locked encounter writeback refusal (encounter-, SOAP-, and Clinical-Notes-level locks), forward-only appointment status state machine including the `patient_tracker_element` sync that keeps the Flow Board aligned, hydration service helpers and orchestrator, past locked-encounter seeder, demo seed/reset contracts, Zoom lookups, protected blueprint endpoints, and migration contract checks.

Latest backend run result in this workspace: `364 passed`.

# Zoom / OpenEMR Integration

Lightweight Flask backend for linking Zoom account data with OpenEMR workflows.

Current implemented areas:
- Zoom account registration + deregistration
- OpenEMR dynamic client registration + registration verification checks
- Provider mapping management (OpenEMR provider <-> Zoom user)
- Appointment type filter management
- OpenEMR appointment webhook handling for create, update, and delete flows
- Meeting lifecycle handling (create/update/recreate/delete) with MeetingRecord persistence
- OpenEMR appointment URL writeback (`pc_hometext` + `pc_website`) after meeting create/recreate
- Audit logging for webhook intake and meeting lifecycle events
- Per-account demo patient contact overrides (`demo_patient_email_override`, `demo_patient_phone_override`)
- OpenEMR listener patch module wiring for `AppointmentSetEvent` and `AppointmentDialogCloseEvent`
- OpenEMR provider + appointment type lookup helpers
- Zoom user lookup helper
- Protected endpoints via `X-API-Key`
- JWKS endpoint for per-account key usage

## Internal Developer Reference

- See [docs/internal/integration-reference.md](docs/internal/integration-reference.md) for:
  - current data model field contracts
  - webhook payload/signature contract
  - OpenEMR appointment status code mapping notes
  - migration and test coverage pointers

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
- `API_KEY`
- `OPENEMR_BASE_URL`
- `OPENEMR_PUBLIC_URL`
- `OPENEMR_FHIR_BASE_URL`
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

Configuration and registration (API key protected):
- `POST /config/register`
- `DELETE /config/register/<zoom_account_id>`
- `GET /config/registrations`
- `POST /config/register/<zoom_account_id>/verify`

Provider mapping management (API key protected):
- `POST /config/providers`
- `GET /config/providers?zoom_account_id=...`
- `DELETE /config/providers/<openemr_provider_id>?zoom_account_id=...`

Appointment filter management (API key protected):
- `POST /config/appointment-types`
- `GET /config/appointment-types?zoom_account_id=...`
- `DELETE /config/appointment-types/<type_id>?zoom_account_id=...`

OpenEMR and Zoom lookup helpers (API key protected):
- `GET /openemr/providers?zoom_account_id=...`
- `GET /openemr/appointment-types`
- `GET /zoom/users?zoom_account_id=...`

## Testing

Run backend tests from the repository root:

```bash
server/scripts/test.sh
```

This script runs `uv run pytest -q` with `UV_CACHE_DIR` pinned to `server/.uv-cache` by default so it works in restricted/sandboxed environments.

Current test suite coverage includes auth/JWKS, registration lifecycle, provider mappings, appointment filters, appointment event processing/webhooks, audit logging, OpenEMR lookups/writeback, demo seed/reset contracts, Zoom lookups, and protected blueprint endpoints.

Latest run result in this workspace: `187 passed`.

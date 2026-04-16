# Zoom / OpenEMR Integration

Lightweight Flask backend for linking Zoom account data with OpenEMR workflows.

Current implemented areas:
- Zoom account registration + deregistration
- OpenEMR dynamic client registration + token verification checks
- Provider mapping management (OpenEMR provider <-> Zoom user)
- Protected API endpoints via `X-API-Key`
- JWKS endpoint for per-account key usage

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
- `APP_PUBLIC_URL`
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
- `DELETE /config/providers/<mapping_id>?zoom_account_id=...`

OpenEMR and Zoom lookup helpers (API key protected):
- `GET /openemr/providers?zoom_account_id=...`
- `GET /zoom/users?zoom_account_id=...`

## Testing

Run backend tests from the repository root:

```bash
server/scripts/test.sh
```

This script runs `uv run pytest -q` with `UV_CACHE_DIR` pinned to `server/.uv-cache` by default so it works in restricted/sandboxed environments.

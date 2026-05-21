# Implementation Setup Guide

This guide is intended to walk through the initial setup, from copying this repository to running the Zoom/OpenEMR integration for evaluation or demo work.

It describes what this repo currently automates, what credentials are required, where those credentials are used, and the setup order. It intentionally avoids environment-specific assumptions that are not encoded in the repository.

## What Gets Deployed

The Docker Compose stack in `docker-compose.yml` defines:

| Service            | Purpose                                                                            |
| ------------------ | ---------------------------------------------------------------------------------- |
| `mariadb`          | OpenEMR database, using MariaDB 11.4                                               |
| `openemr`          | OpenEMR 8.0.0 with repo patch files mounted into the container                     |
| `branding`         | One-shot OpenEMR logo/branding copy job                                            |
| `zoom-module-init` | One-shot OpenEMR module registration job for the appointment listener              |
| `postgres`         | PostgreSQL 16 database for the Flask integration service                           |
| `dbgate`           | DbGate database browser (MariaDB + Postgres), proxied through Flask at `/admin/db` with JWT cookie auth |
| `zoom-bridge`      | Flask integration service plus built React config UI                               |

By default, Docker Compose also reads `docker-compose.override.yml` if present. The current override runs the Flask service in development mode and sets `DATABASE_URL` from `.env`.

## Prerequisites

Install or provide:

- Docker and Docker Compose
- Git
- A public HTTPS URL for OpenEMR
- A public HTTPS URL for the Flask app to receive Zoom webhooks from Zoom
- A Zoom app/account with Server-to-Server OAuth credentials and webhook signing secret

Optional but useful:

- A reverse proxy such as Nginx Proxy Manager, since `docker-compose.yml` exposes OpenEMR on host port `8300` and Flask on host port `5000`
- `openssl` or a password manager for generating local secrets

## Setup Order

1. Clone the repository.

```bash
git clone <repo-url>
cd OpenEMR-Integration
```

2. Copy the example environment file.

```bash
cp .env.example .env
```

3. Fill in `.env` using the variable guide below.

4. Choose the database mode for the Flask integration.

For production-like Docker Compose with PostgreSQL, use the PostgreSQL `DATABASE_URL` form from `.env.example` and start Compose without the development override:

```bash
docker compose -f docker-compose.yml up -d --build
```

For development mode using the override file, Docker Compose will include `docker-compose.override.yml` automatically:

```bash
docker compose up -d --build
```

For local backend development outside Docker, `.env.example` uses `DATABASE_URL=sqlite:///zoomly.db`. For Docker Compose, the clearest copy-and-play path is PostgreSQL with the `POSTGRES_*` variables and the PostgreSQL `DATABASE_URL` form shown in `.env.example`.

5. Wait for OpenEMR and the Flask app to start.

```bash
docker compose ps
```

6. Run Flask database migrations.

The `zoom-bridge` container `CMD` starts Gunicorn directly; it does not run Alembic automatically.

```bash
docker compose exec zoom-bridge uv run alembic upgrade head
```

7. If using the mounted OpenEMR patch helper, fix the ZoomBridge permissions after OpenEMR finishes its first boot.

`server/scripts/start.sh` performs this permission fix after waiting for OpenEMR, but it runs plain `docker compose up -d`, which includes `docker-compose.override.yml` by default:

```bash
server/scripts/start.sh
```

If you intentionally started with `docker compose -f docker-compose.yml ...` to avoid the development override, use the permission commands directly instead:

```bash
docker exec openemr chmod 755 /var/www/localhost/htdocs/openemr/library/zoomly
docker exec openemr chmod 644 /var/www/localhost/htdocs/openemr/library/zoomly/ZoomBridge.php
```

For staging deployments, use `server/scripts/start-staging.sh` instead. It layers the `docker-compose.staging.yml` overlay (extends OpenEMR healthcheck `start_period` to 15 minutes for slower Proxmox hardware), waits for OpenEMR healthy, runs the same permission fixes as `start.sh`, waits for `zoomly-module-init`, then runs `alembic upgrade head`. `git pull` and `docker compose build --no-cache` remain separate deploy steps that run before the script.

8. Confirm service health.

```bash
curl http://localhost:5000/health
curl http://localhost:8300/
```

Adjust hostnames and ports if a reverse proxy is being used.

9. Optional: seed OpenEMR demo data.

Run this after OpenEMR has finished its first boot and the MariaDB container is healthy:

```bash
./seed_data/seed.sh
```

The script loads `MYSQL_ROOT_PASSWORD`, `OPENEMR_DB_NAME`, and optional `MARIADB_CONTAINER` from `.env`. It defaults to the Compose MariaDB container name `mariadb-emr` and database name `openemr`.

Demo patient, provider, nurse, and medical assistant emails are all defined directly in the Sprint 12 seed files — patients in `seed_data/05_patients.sql`, staff in `seed_data/03_staff.sql`. The seed loader (`seed.sh`) cat-pipes `01_globals.sql` through `07_clinical_data.sql` into a single mariadb session so cross-file `@var` references resolve correctly.

To clear the seeded demo data later:

```bash
./seed_data/reset.sh
```

## Environment Variables

Use `.env.example` as the source of truth. Do not commit `.env`.

### Flask And Integration Secrets

| Variable                | What it is used for                                                             | Where to get it                                                       |
| ----------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `ENCRYPTION_KEY`        | Encrypts stored Zoom/OpenEMR secrets and tokens via SQLAlchemy encrypted fields | Generate a long random secret for this deployment                     |
| `KEYS_BASE_DIR`         | Directory where per-account SMART private keys are generated                    | Default in Docker is `/app/keys`, mounted from `./keys`               |
| `SECRET_KEY`            | Flask secret; signs Zoom EHR Context JWTs from `/rest/auth/gettoken`            | Generate a long random secret                                         |
| `CONFIG_ADMIN_PASSWORD` | Password for `POST /api/auth/login` and the React config UI                     | Choose an internal admin password                                     |
| `CONFIG_JWT_SECRET`     | Signs config/admin JWT bearer tokens                                            | Generate a long random secret                                         |
| `OPENEMR_FLASK_SECRET`  | HMAC secret shared by OpenEMR patch code and Flask for OpenEMR-signed requests  | Generate a long random secret and use the same value in both services |

Important: Do not change `ENCRYPTION_KEY` after accounts are registered unless you run the repository's key rotation workflow first. Existing encrypted values become unreadable if the key changes unexpectedly.

### Integration Database

| Variable            | What it is used for                                | Where to get it                                                               |
| ------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------- |
| `DATABASE_URL`      | Flask integration database URL                     | Use PostgreSQL URL for compose/Postgres, or a valid SQLite path for local dev |
| `POSTGRES_DB`       | PostgreSQL database name for `zoomly-postgres`     | Choose a name, for example `zoomly`                                           |
| `POSTGRES_USER`     | PostgreSQL user for the Flask integration database | Choose a user, for example `zoomly`                                           |
| `POSTGRES_PASSWORD` | PostgreSQL password                                | Generate a strong password                                                    |

The compose file overrides `DATABASE_URL` for the `zoom-bridge` service when using only `docker-compose.yml`:

```text
postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
```

### OpenEMR Container And Database

| Variable              | What it is used for                                              | Where to get it                      |
| --------------------- | ---------------------------------------------------------------- | ------------------------------------ |
| `OPENEMR_ADMIN_USER`  | Initial OpenEMR admin username passed into the OpenEMR container | Choose for the demo/deployment       |
| `OPENEMR_ADMIN_PASS`  | Initial OpenEMR admin password passed into the OpenEMR container | Generate or choose a strong password |
| `MYSQL_ROOT_PASSWORD` | MariaDB root password                                            | Generate a strong password           |
| `OPENEMR_DB_USER`     | OpenEMR MariaDB user                                             | Defaults to `openemr` in examples    |
| `OPENEMR_DB_PASS`     | OpenEMR MariaDB user password                                    | Generate a strong password           |
| `OPENEMR_DB_HOST`     | Hostname Flask uses for direct OpenEMR DB access                 | In compose, `mariadb`                |
| `OPENEMR_DB_PORT`     | MariaDB port                                                     | In compose, `3306`                   |
| `OPENEMR_DB_NAME`     | OpenEMR database name                                            | In compose/examples, `openemr`       |
| `MARIADB_CONTAINER`   | Optional container name used by seed/reset scripts               | Defaults to `mariadb-emr`            |

The Flask service builds `OPENEMR_DB_URI` from the `OPENEMR_DB_*` values and uses it for direct SQL queries where no OpenEMR API endpoint exists.

### OpenEMR URLs And SMART Scopes

| Variable                | What it is used for                                                              | Where to get it                                                                                 |
| ----------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `OPENEMR_BASE_URL`      | Internal URL Flask uses to call OpenEMR dynamic registration and token endpoints | In compose, `http://openemr:80`                                                                 |
| `OPENEMR_PUBLIC_URL`    | Public OpenEMR HTTPS URL and OpenEMR OAuth issuer URL                            | Your reverse proxy/DNS URL                                                                      |
| `OPENEMR_FHIR_BASE_URL` | FHIR base URL used by Flask lookup helpers                                       | Public URL plus `/apis/default/fhir`, unless intentionally using the internal compose URL       |
| `OPENEMR_SCOPES`        | SMART Backend Services scopes requested during dynamic client registration       | Use the space-delimited scope list in `.env.example` unless the integration requirements change |
| `APP_PUBLIC_URL`        | Public Flask URL                                                                 | Your reverse proxy/DNS URL for the Flask app                                                    |
| `APP_INTERNAL_URL`      | Internal Flask URL used for JWKS and callback URIs during OpenEMR registration   | In compose, `http://zoom-bridge:5000`                                                           |

The OpenEMR container receives `OPENEMR_SETTING_site_addr_oath=${OPENEMR_PUBLIC_URL}`. This must match the public OpenEMR URL used for OAuth/FHIR flows.

### Logging

| Variable    | What it is used for          |
| ----------- | ---------------------------- |
| `LOG_LEVEL` | Flask log level              |
| `LOG_FILE`  | Rotating Flask log file path |

In Docker, `./server/logs` is mounted to `/app/logs`.

## Zoom App Credentials

The React config UI registers Zoom accounts into the Flask database. Those values are not hard-coded in `.env`; they are entered through the config UI and stored encrypted.

Required registration fields:

| Field                 | What it is used for                                                     | Where to get it                                            |
| --------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------- |
| `zoom_account_id`     | Zoom account-level identifier used with the `account_credentials` grant | From the Zoom app/account credentials page                 |
| `zoom_client_id`      | Zoom OAuth client ID                                                    | From the Zoom app credentials page                         |
| `zoom_client_secret`  | Zoom OAuth client secret                                                | From the Zoom app credentials page                         |
| `zoom_webhook_secret` | Secret used to verify Zoom webhook signatures                           | From the Zoom app webhook/event subscription configuration |
| `contact_email`       | Sent to OpenEMR dynamic registration as the SMART client contact        | Internal owner/admin email                                 |

Optional registration fields:

| Field                  | What it is used for                                                                    |
| ---------------------- | -------------------------------------------------------------------------------------- |
| `nickname`             | Display label in the config UI                                                         |
| `timezone`             | Used for Zoom meeting scheduling and EHR appointment window conversion. Defaults to ET |
| `ehr_context_username` | Basic Auth username Zoom will use for `/rest/auth/gettoken`                            |
| `ehr_context_password` | Basic Auth password Zoom will use for `/rest/auth/gettoken`; Flask stores only a hash  |

During registration, the Flask service:

1. Generates a per-account RSA keypair under `KEYS_BASE_DIR`.
2. Dynamically registers a SMART Backend Services client with OpenEMR at `/oauth2/default/registration`.
3. Auto-enables the new OpenEMR client via direct DB `UPDATE oauth_clients SET is_enabled = 1`. On failure, deregisters from OpenEMR, deletes the keypair, and aborts.
4. Stores the OpenEMR registration metadata and Zoom credentials.
5. Validates Zoom credentials by requesting a Zoom Server-to-Server OAuth token.
6. Generates a deterministic `tenant_id` from Zoom account ID and client ID.

## OpenEMR Patch Behavior

When using `docker-compose.yml`, the repo mounts OpenEMR patch files directly into the OpenEMR container:

- `patches/AuthorizationController.php`
- `patches/OAuth2AuthorizationListener.php`
- `patches/RsaSha384Signer.php` — fixes a multi-client JWT verification bug in OpenEMR (S7-08); without this patch, any account whose key isn't first in the JWKS response fails token verification
- `patches/zoom_appointment_listener/*`
- `patches/add_edit_event.php`
- `patches/post_calendar/ajax_template.html`
- `patches/clinical_note_fetcher/*`
- `patches/library/zoomly/ZoomBridge.php`

The `zoom-module-init` service inserts or activates the `zoom_appointment_listener` module row in OpenEMR's `modules` table.

The OpenEMR patch helper `ZoomBridge.php` sends signed requests to:

```text
http://zoom-bridge:5000
```

That hostname works on the Docker Compose network. If installing patches into a separate/non-compose OpenEMR environment, update the helper target or provide equivalent DNS/network routing.

## First Configuration In The React UI

1. Open the Flask app in a browser.

Local Docker default:

```text
http://localhost:5000
```

2. Log in with `CONFIG_ADMIN_PASSWORD`.

3. Register a Zoom account from the config UI.

Enter the Zoom account credentials and optional EHR Context credentials. On success, the response and account detail view include:

**Read Only**

- Zoom Account ID
- Zoom Client ID
- OpenEMR Client ID
- `tenant_id` as X-Tenant-ID

**Editable**

- Nickname
- EHR Context Username field - Will initially be blank
- EHR Context Password field - Will be blank - Leave blank to keep current value
- Zoom Client Secret field - Leave blank to keep current value
- Zoom Webhook Secret field - Leave blank to keep current value

4. (Auto-handled) Confirm the OpenEMR client is enabled.

Registration auto-enables the dynamically registered OpenEMR client by flipping `oauth_clients.is_enabled = 1` via direct DB UPDATE right after the RFC 7591 call returns. No manual "Enable Client" step in OpenEMR Admin is needed. If anything downstream of the OpenEMR registration fails — the enable UPDATE, the Flask `ZoomAccount` persist, or Zoom credential validation — registration rolls back: the OpenEMR client is deregistered, the local keypair is deleted, and the registration UI surfaces the error. The OpenEMR side never ends up with an enabled-but-orphaned client.

If you want to verify after the fact, navigate to Admin → System → API Clients in OpenEMR and confirm the entry **Zoomly Bridge - `Zoom Account ID`** shows as enabled.

5. Configure appointment type filters.

Only matching OpenEMR appointment categories/list option IDs pass through to Zoom meeting creation.

6. Configure account settings.

Available settings include:

- timezone
- shared Zoom user behavior - Enable/disable multiple providers to single Zoom user
- clinical note writeback mode: `both`, `clinical_note_only`, or `soap_only`
- demo patient email/phone overrides
  - Currently this does nothing either way. No patient communication occurs during demos.

7. Configure provider mappings.

Use the config UI to map:

- 1 OpenEMR provider to 1 Zoom user account
- Multiple OpenEMR providers can be mapped to a single Zoom user account during testing.
  - Configuration flag enabled/disabled on the Account Config page.

Provider mappings are required before appointment webhooks can create/update meetings.

## Zoom Webhook Setup

Configure the Zoom Server to Server app to send webhooks to the public Flask URL:

Navigate to marketplace.zoom.us, sign in, and click manage in the top right. Find the correct zoom app and navigate to the Feature page.

This page provides the webhook signing secret used as `zoom_webhook_secret` during account registration.

Enable Event Subsciptions and then add a new Event Subscription.

Enter the url for Zoom to deliver the event notifications to and click the Validate the URL button (required by Zoom).
Note: ensure the account is fully registered to the integration service and enabled in OpenEMR or validation will fail.

```text
https://<flask-public-host>/webhooks/zoom
```

Currently required Zoom events in code:

- `clinical_notes.note_created`
- `meeting.started`
- `meeting.participant_joined_waiting_room`
- `meeting.participant_jbh_waiting`

## Zoom EHR Context Setup

The EHR Context endpoints are:

```text
GET  /rest/auth/gettoken
POST /rest/openendpoint/service/getAppointments
```

**REQUIRED:**

- Enable NovelVox integration flag in OP
- Once enabled, navigate to Account Management -> Account Settings -> Clincial Note in the Zoom Admin portal
- Enable NovelVox integration
- Add:
  - endpoint of the Flask service
  - X-Tenant-ID=`tenant_id`
  - JWT Username=`ehr_context_username`
  - JWT Password=`ehr_context_password`

In the Zoom meeting, when a new Clinical Note session is initiated Zoom sends:

- `X-Tenant-ID: <tenant_id>`
- Basic Auth credentials matching the `ehr_context_username` / `ehr_context_password` saved during registration

`/rest/auth/gettoken` returns a short-lived JWT. Zoom then calls `getAppointments` with:

- `Authorization: Bearer <token>`
- the same `X-Tenant-ID`
- a request body containing `dateTime` and `zoomUserId`

The `tenant_id` is generated by Flask and shown in the config UI after registration.

## Smoke Test Checklist

1. `GET /health` returns `{"status": "ok", ...}`.
2. The config UI login works with `CONFIG_ADMIN_PASSWORD`.
3. `GET /.well-known/jwks.json` returns keys after a Zoom account is registered.
4. A Zoom account registration succeeds and shows `tenant_id`.
5. OpenEMR verification succeeds — the client is auto-enabled at registration time.
6. Provider mappings can be created.
7. Appointment type filters can be created.
8. Creating or updating a matching OpenEMR appointment sends a signed `appointment.set` webhook to Flask.
9. Flask creates or updates a Zoom meeting and writes the Zoom start URL to OpenEMR `pc_website`, which is displayed beyond a Zoom icon on the Appointment Card in the OpenEMR Scheduler.
10. Deleting a linked appointment sends `appointment.deleted`. The Zoom meeting is removed; the local `MeetingRecord` is removed only when no `ClinicalNoteRecord` exists for it. When a note has been received, the row is preserved with `status="cancelled"` to keep the audit trail.
11. Zoom waiting-room or meeting-start webhooks update audit logs and meeting state.
12. Zoom clinical note webhooks create `ClinicalNoteRecord` rows and write notes to OpenEMR according to `note_writeback_mode`.

## Operational Notes

- Back up `openemr_sites`, MariaDB data, PostgreSQL data, and generated keys before upgrades.
- Keep `ENCRYPTION_KEY`, `CONFIG_JWT_SECRET`, `SECRET_KEY`, `OPENEMR_FLASK_SECRET`, database passwords, and Zoom client secrets out of Git.
- If `ENCRYPTION_KEY` must rotate, use `server/scripts/rotate-encryption-key.py`; do not simply replace the value in `.env`.
- `server/scripts/test.sh` runs the backend test suite with a sandbox-friendly UV cache.

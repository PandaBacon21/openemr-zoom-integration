# Implementation Setup Guide

This guide is intended to walk through the initial setup, from copying this repository to running the Zoom/OpenEMR integration for evaluation or demo work.

It describes what this repo currently automates, what credentials are required, where those credentials are used, and the setup order. It intentionally avoids environment-specific assumptions that are not encoded in the repository.

## What Gets Deployed

The Docker Compose stack in `docker-compose.yml` defines:

| Service            | Purpose                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------- |
| `mariadb`          | OpenEMR database, using MariaDB 11.4                                                                    |
| `openemr`          | Custom OpenEMR 8.0.0 image built from `openemr/Dockerfile` — bakes in every PHP patch from `openemr/patches/` and every Zoom-branded asset from `openemr/branding/`. Tagged `zoomly-openemr:local`. |
| `zoom-module-init` | One-shot OpenEMR module registration job for the appointment listener                                   |
| `postgres`         | PostgreSQL 16 database for the Flask integration service                                                |
| `dbgate`           | DbGate database browser (MariaDB + Postgres), proxied through Flask at `/admin/db` with JWT cookie auth. **Non-prod only** — gated behind the `non-prod` compose profile and the `ENABLE_DBGATE` env var on `zoom-bridge` |
| `zoom-bridge`      | Flask integration service plus built React config UI                                                    |

By default, Docker Compose also reads `docker-compose.override.yml` if present. The current dev override replaces the Flask container's CMD with `flask run --debug` (hot-reload), sets `FLASK_ENV=development` / `FLASK_DEBUG=true`, bind-mounts `./server/app`, `./server/tests`, and `./seed_data` into the Flask container, **and** bind-mounts every file in `openemr/patches/` over the baked OpenEMR image so PHP edits take effect on a page refresh without rebuilding the image. A committed template lives at `docker-compose.override.yml.example` — on a fresh clone, copy it to `docker-compose.override.yml`. Passing `-f` explicitly (as `start-staging.sh`, `start-prod.sh`, and `start-dev.sh --baked` do) bypasses the override and runs the production-shaped gunicorn-gevent config against the baked OpenEMR image.

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

4. Start the stack.

PostgreSQL is the only supported Flask-side database — both dev and staging use it (the `zoomly-postgres` container started by Compose). SQLite is no longer a supported option.

For dev with hot-reload via the override file:

```bash
docker compose --profile non-prod up -d --build
```

For staging-shaped behavior (no dev override, gunicorn-gevent, baked image):

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml --profile non-prod up -d --build
```

For production deploys, omit the `--profile non-prod` flag so DbGate is excluded.

`DATABASE_URL` in `.env` should use the PostgreSQL form from `.env.example` (`postgresql+psycopg2://...@postgres:5432/...`). The compose file interpolates the `POSTGRES_*` env vars into this URL for the `zoom-bridge` service.

5. Wait for OpenEMR and the Flask app to start.

```bash
docker compose ps
```

6. Run Flask database migrations.

The `zoom-bridge` container `CMD` starts Gunicorn directly; it does not run Alembic automatically.

```bash
docker compose exec zoom-bridge uv run alembic upgrade head
```

7. Use the appropriate startup script for your environment.

`server/scripts/start-dev.sh` runs `docker compose --profile non-prod up -d` (auto-loading `docker-compose.override.yml`) so DbGate is included for the dev non-prod build, waits for OpenEMR to be healthy, then runs a chmod pass against the bind-mounted patch files (which inherit host ownership and need `apache:apache` + `644` to satisfy OpenEMR):

```bash
server/scripts/start-dev.sh
```

To simulate staging/prod locally — running the baked `zoomly-openemr:local` image with no patch shadowing and gunicorn instead of the Flask dev server — pass `--baked`. The script then uses an explicit `-f docker-compose.yml` to bypass the override and skips the chmod block (the baked image already has correct ownership):

```bash
server/scripts/start-dev.sh --baked
```

For staging deployments, use `server/scripts/start-staging.sh`. It layers the `docker-compose.staging.yml` overlay (extends OpenEMR healthcheck `start_period` to 15 minutes for slower Proxmox hardware), waits for OpenEMR healthy, waits for `zoomly-module-init`, then runs `alembic upgrade head`. No chmod block is needed — the baked image is authoritative. `git pull` and `docker compose build --no-cache` remain separate deploy steps that run before the script.

For production deployments, use `server/scripts/start-prod.sh`. It runs with only `-f docker-compose.yml` (no overrides, no staging overlay), omits `--profile non-prod` so DbGate is not started, and runs `alembic upgrade head` at the end. `ENABLE_DBGATE` must remain unset or `false` so the Flask `/admin/db` proxy is never registered.

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

Current seed shape: 4 facilities, 18 patient-panel providers, 108 patients (PIDs 100-207), 292 weekday appointments, regional pharmacies/payers, complete patient contact/insurance fields, and provider+nurse care teams.

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
| `API_KEY`               | API key for protected endpoint guard middleware                                 | Generate a long random secret                                         |
| `ENABLE_DBGATE`         | Gates the DbGate database browser proxy at `/admin/db` and the React Database nav. Set `true` in dev/staging; leave unset or `false` in production | One of: `true`, `false` (default `false`)                             |
| `ENABLE_EPIC_ZCC`       | Gates the Epic-style ZCC CTI middleware blueprints and React Epic ZCC config tab. Leave `false` unless configuring ZCC CTI demos | One of: `true`, `false` (default `false`)                             |

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
| `OPENEMR_FHIR_BASE_URL` | FHIR base URL used by Flask lookup helpers                                       | Internal compose URL plus `/apis/default/fhir` — `http://openemr:80/apis/default/fhir`. `docker-compose.yml` pins this on `zoom-bridge`, and a compose `environment:` value overrides `.env`, so setting a public URL here has no effect. Leave it internal. |
| `OPENEMR_SCOPES`        | SMART Backend Services scopes requested during dynamic client registration       | Use the space-delimited scope list in `.env.example` unless the integration requirements change |
| `APP_PUBLIC_URL`        | Public Flask URL                                                                 | Your reverse proxy/DNS URL for the Flask app                                                    |
| `APP_INTERNAL_URL`      | Internal Flask URL used for JWKS and callback URIs during OpenEMR registration   | In compose, `http://zoom-bridge:5000`                                                           |
| `EPIC_ZCC_CLIENT_ID`    | Global client ID shown in the Epic ZCC admin tab and expected by ZCC CTI auth    | Choose/provision for the ZCC Epic integration                                                    |
| `ZOOMLY_EPIC_ZCC_CLIENT_URL` | Optional OpenEMR top-nav CTI iframe URL for the Epic-ZCC callbar shell      | ZCC/CCSE URL when rendering the callbar inside OpenEMR                                           |

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

### Zoom S2S OAuth Scopes

The Zoom S2S OAuth app (created in Zoom Marketplace) must have the following scopes enabled. Without a scope, Zoom returns `401 Unauthorized` on the corresponding endpoint and the Flask error log shows the URL that was rejected. Scopes are added in the Zoom Marketplace app's **Scopes** tab; new scopes take effect on the next token mint.

| Feature | Endpoint(s) Zoomly hits | Required scope(s) |
| --- | --- | --- |
| List Zoom users (provider mapping dropdown) | `GET /users` | `user:read:list_users:admin` |
| Read a single Zoom user (profile timezone for meeting host) | `GET /users/{userId}` | `user:read:user:admin` |
| Create / read / update / delete Zoom meetings (telehealth flow) | `POST /users/{userId}/meetings`, `GET/PATCH/DELETE /meetings/{meetingId}` | `meeting:read:meeting:admin`, `meeting:write:meeting:admin`, `meeting:update:meeting:admin`, `meeting:delete:meeting:admin` |
| Read Zoom clinical notes (note writeback flow) | `GET /clinical_notes/...` | `clinical_notes:read:admin` (verify in Marketplace UI) |
| **List ZCC users (CTI agent mapping dropdown — Sprint 11)** | `GET /contact_center/users` | `contact_center_user:read:list:admin` |

If you add a new Zoom API endpoint to Flask and get a 401 on first call, check this table and the Zoom Marketplace app's Scopes tab — the most common cause is a missing scope. The Flask error log will print `Failed to fetch ... 401 Client Error: Unauthorized for url: <endpoint>` which tells you which endpoint to scope-check.

## OpenEMR Patch Behavior

OpenEMR patch files are baked into the custom `zoomly-openemr:local` image at build time by `openemr/Dockerfile` (every file under `openemr/patches/` is COPY'd with `apache:apache` ownership and `644` perms). The base file set:

- `openemr/patches/AuthorizationController.php`
- `openemr/patches/OAuth2AuthorizationListener.php`
- `openemr/patches/RsaSha384Signer.php` — fixes a multi-client JWT verification bug in OpenEMR (S7-08); without this patch, any account whose key isn't first in the JWKS response fails token verification
- `openemr/patches/zoom_appointment_listener/*`
- `openemr/patches/add_edit_event.php`
- `openemr/patches/post_calendar/ajax_template.html`
- `openemr/patches/clinical_note_fetcher/*`
- `openemr/patches/epic_cti/*`
- `openemr/patches/library/zoomly/ZoomBridge.php`

In dev, `docker-compose.override.yml` bind-mounts these same files over the baked copies so PHP edits take effect on a page refresh without rebuilding the image. `start-dev.sh --baked` skips the override to verify the baked image; staging and prod scripts always run image-authoritative.

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
- clinical note writeback mode: `both`, `clinical_note_only`, or `soap_only`
- demo patient email/phone overrides
  - Currently this does nothing either way. No patient communication occurs during demos.

7. Configure user mappings.

Use the config UI to map:

- OpenEMR provider-role users to Zoom users for telehealth meeting creation
- ZCC agent-role users to Zoom/ZCC users for Epic-ZCC screen-pop routing
- A single mapping row can carry both roles when the same OpenEMR user is both a provider and a ZCC agent

Provider-role mappings are required before appointment webhooks can create/update meetings. ZCC-agent-role mappings are required before Epic-ZCC screen-pop bootstrap can return stream URLs for an OpenEMR user.

## Epic-ZCC CTI Setup

This path is optional and disabled by default.

1. Set `ENABLE_EPIC_ZCC=true` on `zoom-bridge`.
2. Register or select a Zoom account in the admin UI.
3. Open the account's Epic ZCC tab and initialize credentials. This generates the per-account `epic_kid`; the Client ID shown in the UI comes from `EPIC_ZCC_CLIENT_ID`.
4. In the Zoom Admin Portal, configure the ZCC Epic integration connection settings with the generated instance URL and JWKS URL:

```text
Instance URL: https://<flask-public-host>/zoomly/<zoom_account_id>/interconnect-amcurprd-oauth
JWKS URL:     https://<flask-public-host>/zoomly/<zoom_account_id>/interconnect-amcurprd-oauth/oauth2/keys/1/<epic_kid>
```

5. Save the remaining Zoom Admin Portal fields from the Epic ZCC tab:
   - Connection Name
   - Phone System ID and type
   - Background User ID and type
   - Recipient ID Type
   - ZCC Backend URL
6. Map OpenEMR users to Zoom users with `is_zcc_agent=true` and a matching `zcc_user_id`. Provider-role mappings can remain enabled on the same row.
7. Configure `ZOOMLY_EPIC_ZCC_CLIENT_URL` when the OpenEMR top-nav callbar iframe should render.

Operational notes:

- OpenEMR click-to-call controls render only for logged-in users whose bootstrap call returns active ZCC-agent streams. Non-ZCC users do not load the callbar/subscriber assets and see plain phone numbers in demographics, patient finder, and appointment-card views.
- Demo seed phone numbers ending in `555-####` are intentionally not clickable, even for ZCC-agent sessions, so synthetic demo numbers are not dialed through ZCC.
- **Provider inbound calls** use a different screen-pop path than patient calls. A ReceiveCommunication3 with `LookupType="Provider"` resolves the NPI or Tax ID directly from the RC3 `LookupID` against OpenEMR's Address Book population (internal clinicians and external providers) via `find_address_book_providers` — there is no Practitioner.Search cache dependency, because ZCC does not call Practitioner.Search during a call. A single match pops that entry's `addrbook_edit.php` modal; no match opens the Address Book list. NPI is unique, so there is no provider multi-match picker. The Practitioner.Search FHIR endpoint still exists as a spec-compliant directory, but its phone-keyed cache is only a fallback.
- **Bearer token model:** each account holds one reusable account-level bearer token. `POST /oauth2/token` returns the account's existing valid token and only re-mints within roughly 60s of expiry. The token authenticates the ZCC→Zoomly call at the account level — agent identity comes from the RC3 `RecipientID`, not the token — so all agents share a single account token and many can be concurrent. The token is persisted encrypted on `zoom_accounts` to survive restarts, and the guard validates the in-memory store with a DB-token fallback.
- PatientLookUp results are held in a short process-local cache for ReceiveCommunication3. The cache is keyed by account + normalized phone number, is single-use once consumed by ReceiveCommunication3, and uses the same short TTL as PatientLookUp.
- Outbound click-to-dial does not use a separate outbound-call cache. After ZCC accepts the initiate-call request, the route preloads the PatientLookUp cache with the known OpenEMR patient under the normalized dialed phone number and marks the cached row with `matched_on=outbound_context`.
- Gunicorn currently runs one worker, so the process-local cache is consistent inside one Flask process. A future multi-worker or multi-replica deployment would need a shared cache or a different screen-pop correlation strategy.

## Zoom Webhook Setup

Configure the Zoom Server to Server app to send webhooks to the public Flask URL:

Navigate to marketplace.zoom.us, sign in, and click manage in the top right. Find the correct zoom app and navigate to the Feature page.

This page provides the webhook signing secret used as `zoom_webhook_secret` during account registration.

Enable Event Subsciptions and then add a new Event Subscription.

Enter the url for Zoom to deliver the event notifications to and click the Validate the URL button (required by Zoom).
Note: ensure the account is fully registered to the integration service and enabled in OpenEMR or validation will fail.

```text
https://<flask-public-host>/webhooks/zoom/<zoom_account_id>
```

The webhook path is **per-account** — replace `<zoom_account_id>` with the Zoom Account ID for the account this Marketplace app belongs to. CRC URL validation uses the path account_id to resolve the correct `webhook_secret`; non-CRC events cross-check `payload.account_id` against the path as defense-in-depth.

Currently required Zoom events in code:

- `clinical_notes.note_created` — triggers the immediate note-fetch + writeback to OpenEMR
- `meeting.started` — flips appointment status to In Exam Room
- `meeting.ended` — flips appointment status to Checked Out
- `meeting.participant_jbh_waiting` — patient-arrived signal (fires when participant clicks join URL before host starts the meeting). Required for the Arrived status + pre-host encounter creation.
- `meeting.participant_joined_waiting_room` _(optional / defensive)_ — only fires after the host has joined, so it doesn't actually drive any new lifecycle state. Kept subscribed as a safety net; can be omitted without affecting the demo.

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

## Domain Migration

Moving the deployment to a new public domain (for example off an old proxy hostname onto the current `zoomlyhealth.com` hosts) touches DNS, the reverse proxy, `.env`, the OpenEMR `globals` table, and every stored Zoom-account registration. The current hosts are:

| Environment | OpenEMR (EHR) | Flask bridge |
| ----------- | -------------------------------- | ----------------------------------- |
| Dev | `https://zhr-dev.zoomlyhealth.com` | `https://bridge-dev.zoomlyhealth.com` |
| Staging/Prod | `https://zhr.zoomlyhealth.com` | `https://bridge.zoomlyhealth.com` |

Staging and prod currently share a single host — there is no separate staging/prod split at present.

Runbook:

1. **DNS** — add A/AAAA (or CNAME) records for the new hostnames pointing at the host: `zhr` + `bridge` for staging/prod, and `zhr-dev` + `bridge-dev` for dev.
2. **Nginx Proxy Manager** — add proxy hosts and request TLS certificates for each new hostname. OpenEMR forwards to `openemr:80` (or `:8300` on the host); the bridge forwards to `zoom-bridge:5000`.
3. **`.env`** — set `OPENEMR_PUBLIC_URL` and `APP_PUBLIC_URL` to the new domain. Leave the internal container URLs unchanged: `OPENEMR_BASE_URL=http://openemr:80`, `OPENEMR_FHIR_BASE_URL=http://openemr:80/apis/default/fhir`, `APP_INTERNAL_URL=http://zoom-bridge:5000`. Only the two `*_PUBLIC_URL` values carry the public domain.
4. **Redeploy (image-authoritative)** — staging/prod are image-authoritative, so rebuild the OpenEMR image and redeploy to pick up any patch changes, then bring the stack up so containers are recreated with the new `.env`:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.staging.yml build --no-cache
   server/scripts/start-staging.sh
   ```

   `start-staging.sh` does not build — the build is a separate step. `up -d` recreates containers so the new `.env` takes effect.
5. **OpenEMR DB globals** — `OPENEMR_SETTING_*` env vars only apply on first init, so an already-initialized OpenEMR keeps the old domain in its `globals` table. Update `site_addr_oath` and `portal_onsite_two_address` directly (or do a fresh init). Find the stale rows first:

   ```sql
   SELECT gl_name, gl_value FROM globals WHERE gl_value LIKE '%<old-domain>%';
   ```

   This step is required: Flask signs the OAuth2 `aud` claim with the new domain, and OpenEMR must expect the same value or the OAuth2/FHIR token flow breaks.
6. **Re-seed** — run `./seed_data/reset.sh && ./seed_data/seed.sh`. The patient-portal URL is env-driven now, so the seed picks up the new domain.
7. **Re-register each Zoom account** — existing registrations baked the old domain into OpenEMR's `oauth_clients` row and the JWT `aud`; editing `.env` does not rewrite stored registrations. De-register and re-register each account from the config UI. **Known limitation:** a full de-register/re-register is currently required — there is no in-place registration-domain migration yet.
8. **Update Zoom portal URLs** — repoint every URL configured in the Zoom Marketplace/Admin portal to the new domain: the webhook URL, the EHR Context endpoint, and the Epic-ZCC Instance URL + JWKS URL.
9. **Verify** — confirm admin login, a registration verify (OAuth), a webhook delivery, the patient-portal link, and a screen-pop.

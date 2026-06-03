# Zoomly Internal Integration Reference

Internal developer notes for the Zoom <-> OpenEMR bridge.  
This is a working reference for model contracts, webhook payload expectations, and integration-specific code mappings.

Related planning:

- [Architecture & Deployment Handoff](../../ARCHITECTURE.md) is the top-level system view — service topology, network segmentation, data flow sequences, env var inventory, and the K8s migration must / should / preserve summary.
- [Implementation Setup Guide](implementation-setup-guide.md) explains repo-based deployment, required credentials, and first-run setup.
- [Phase 2 Sprint Plan](phase-2-sprint-plan.md) tracks Phase 2 Sprint 7-13 (Sprints 9, 10, 11 were skipped — see the sprint plan file for the renumbering).

## Data Models

### `zoom_accounts` (`ZoomAccount`)

| Column                              | Type                         | Required | Notes                                                          |
| ----------------------------------- | ---------------------------- | -------- | -------------------------------------------------------------- |
| `account_id`                        | `String(128)`                | yes      | Zoom account-level identifier, primary key                     |
| `key_version`                       | `Integer`                    | yes      | Encryption key version used for row-level secrets              |
| `nickname`                          | `String(128)`                | no       | Optional display name for the registration/config UI           |
| `client_id`                         | `String(128)`                | yes      | Zoom OAuth client ID                                           |
| `client_secret`                     | `EncryptedType(String(256))` | yes      | Zoom OAuth client secret (encrypted at rest)                   |
| `webhook_secret`                    | `EncryptedType(String(256))` | no       | Zoom webhook secret (encrypted at rest)                        |
| `tenant_id`                         | `String(10)`                 | no       | Zoom EHR Context tenant ID used in `X-Tenant-ID`               |
| `ehr_context_username`              | `String(128)`                | no       | Basic Auth username for Zoom EHR Context token exchange        |
| `ehr_context_password_hash`         | `String(256)`                | no       | Hashed EHR Context Basic Auth password                         |
| `zoom_access_token`                 | `EncryptedType(Text)`        | no       | Cached Zoom token (encrypted at rest)                          |
| `zoom_token_expires_at`             | `DateTime(timezone=True)`    | no       | Zoom token expiry                                              |
| `openemr_client_id`                 | `String(256)`                | no       | Dynamic registration client ID from OpenEMR                    |
| `openemr_client_secret`             | `EncryptedType(String(256))` | no       | OpenEMR dynamic registration client secret (encrypted at rest) |
| `openemr_registration_access_token` | `EncryptedType(Text)`        | no       | Registration management token (encrypted at rest)              |
| `openemr_registration_client_uri`   | `String(512)`                | no       | Registration management URI                                    |
| `openemr_access_token`              | `EncryptedType(Text)`        | no       | Cached OpenEMR access token (encrypted at rest)                |
| `openemr_token_expires_at`          | `DateTime(timezone=True)`    | no       | OpenEMR token expiry                                           |
| `private_key_path`                  | `String(512)`                | no       | Filesystem path to per-account private key                     |
| `kid`                               | `String(256)`                | no       | JWKS key id used for private_key_jwt                           |
| `is_active`                         | `Boolean`                    | yes      | Soft-active registration state                                 |
| `created_at`                        | `DateTime(timezone=True)`    | yes      | Created timestamp (UTC)                                        |
| `updated_at`                        | `DateTime(timezone=True)`    | yes      | Updated timestamp (UTC)                                        |

Relationships:

- `config` -> `AccountConfig | None`
- `provider_mappings` -> `ProviderMapping[]`
- `appointment_type_filters` -> `AppointmentTypeFilter[]`
- `meeting_records` -> `MeetingRecord[]`

### `account_configs` (`AccountConfig`)

| Column                                | Type                      | Required | Notes                                                                                                            |
| ------------------------------------- | ------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------- |
| `account_id`                          | `String(128, FK)`         | yes      | Primary key and FK to `zoom_accounts.account_id`                                                                 |
| `timezone`                            | `String(64)`              | yes      | Account-level IANA timezone, used as the *fallback* for Zoom meeting scheduling when a mapped provider has no `ProviderMapping.zoom_user_timezone` set. Also used for EHR appointment window conversion. Default `America/New_York` |
| `allow_shared_zoom_user`              | `Boolean`                 | yes      | Allows shared Zoom user behavior in config workflows; default `false`                                            |
| `demo_patient_email_override_enabled` | `Boolean`                 | yes      | Enables demo patient email override                                                                              |
| `demo_patient_email_override`         | `String(256)`             | no       | Optional demo override for patient email communications                                                          |
| `demo_patient_phone_override_enabled` | `Boolean`                 | yes      | Enables demo patient phone override                                                                              |
| `demo_patient_phone_override`         | `String(32)`              | no       | Optional demo override for patient phone/SMS communications                                                      |
| `note_writeback_mode`                 | `String(32)`              | yes      | Controls note writeback target: `both`, `clinical_note_only`, or `soap_only`; default `both`                     |
| `created_at`                          | `DateTime(timezone=True)` | no       | Created timestamp (UTC)                                                                                          |
| `updated_at`                          | `DateTime(timezone=True)` | no       | Updated timestamp (UTC)                                                                                          |

### `provider_mappings` (`ProviderMapping`)

| Column                           | Type                      | Required | Notes                                                                    |
| -------------------------------- | ------------------------- | -------- | ------------------------------------------------------------------------ |
| `id`                             | `Integer`                 | yes      | Primary key                                                              |
| `zoom_account_id`                | `String(128, FK)`         | yes      | FK to `zoom_accounts.account_id`                                         |
| `openemr_fhir_id`                | `String(128)`             | yes      | OpenEMR practitioner FHIR id                                             |
| `openemr_provider_npi`           | `String(10)`              | yes      | Provider NPI used by filter pipeline                                     |
| `openemr_provider_id`            | `String(128)`             | no       | OpenEMR `users.id` / appointment `provider_id` used for webhook matching |
| `openemr_provider_name`          | `String(256)`             | no       | Provider display name                                                    |
| `openemr_facility_id`            | `Integer`                 | no       | OpenEMR `users.facility_id` captured at mapping creation (S7-14)         |
| `openemr_facility_name`          | `String(255)`             | no       | OpenEMR `users.facility` (display name) captured at mapping creation     |
| `zoom_user_email`                | `String(256)`             | yes      | Zoom host email                                                          |
| `zoom_user_name`                 | `String(256)`             | no       | Zoom display name                                                        |
| `zoom_user_id`                   | `String(128)`             | no       | Zoom user id                                                             |
| `zoom_user_type`                 | `Integer`                 | no       | Zoom license/type                                                        |
| `zoom_user_timezone`             | `String(64)`              | no       | IANA timezone from the mapped Zoom user's profile (e.g. `America/Denver`). Used when scheduling Zoom meetings for this provider — `AccountConfig.timezone` is the fallback when this is NULL (Zoom user with no profile TZ, or mapping created before this field shipped) |
| `default_alternative_host_email` | `String(256)`             | no       | Default alternative host                                                 |
| `is_active`                      | `Boolean`                 | yes      | Active mapping flag                                                      |
| `created_at`                     | `DateTime(timezone=True)` | no       | Created timestamp (UTC)                                                  |

### `appointment_type_filters` (`AppointmentTypeFilter`)

| Column              | Type                      | Required | Notes                                                 |
| ------------------- | ------------------------- | -------- | ----------------------------------------------------- |
| `id`                | `Integer`                 | yes      | Primary key                                           |
| `zoom_account_id`   | `String(128, FK)`         | yes      | FK to `zoom_accounts.account_id`                      |
| `openemr_type_id`   | `String(128)`             | yes      | OpenEMR appointment category/list option id           |
| `openemr_type_name` | `String(256)`             | yes      | OpenEMR appointment category/list option display name |
| `created_at`        | `DateTime(timezone=True)` | no       | Created timestamp (UTC)                               |

### `meeting_records` (`MeetingRecord`)

| Column                   | Type                      | Required | Notes                                                                      |
| ------------------------ | ------------------------- | -------- | -------------------------------------------------------------------------- |
| `zoom_meeting_id`        | `String(128)`             | yes      | Zoom meeting ID, primary key                                               |
| `zoom_account_id`        | `String(128, FK)`         | yes      | FK to `zoom_accounts.account_id`                                           |
| `zoom_start_url`         | `String(1024)`            | no       | Host/alt-host start URL                                                    |
| `zoom_join_url`          | `String(1024)`            | no       | Patient join URL                                                           |
| `alternative_host_email` | `String(256)`             | no       | Captured alternative host                                                  |
| `openemr_appointment_id` | `String(128)`             | yes      | OpenEMR appointment/event id                                               |
| `openemr_provider_id`    | `String(128)`             | yes      | OpenEMR provider id (`users.id`)                                           |
| `openemr_appt_status`    | `String(16)`              | no       | OpenEMR `apptstat`/`pc_apptstatus` code                                    |
| `status`                 | `String(64)`              | yes      | Internal progression status (for workflow orchestration)                   |
| `meeting_started_at`     | `DateTime(timezone=True)` | no       | Timestamp for when the Zoom meeting/arrival flow marks the meeting started |
| `created_at`             | `DateTime(timezone=True)` | no       | Created timestamp (UTC)                                                    |
| `updated_at`             | `DateTime(timezone=True)` | no       | Updated timestamp (UTC)                                                    |

Relationships:

- `patients` -> `MeetingPatient[]`
- `clinical_note` -> `ClinicalNoteRecord | None`

### `meeting_patients` (`MeetingPatient`)

| Column               | Type                      | Required | Notes                                                         |
| -------------------- | ------------------------- | -------- | ------------------------------------------------------------- |
| `id`                 | `Integer`                 | yes      | Primary key                                                   |
| `zoom_meeting_id`    | `String(128, FK)`         | yes      | FK to `meeting_records.zoom_meeting_id` (`ON DELETE CASCADE`) |
| `openemr_patient_id` | `String(128)`             | yes      | OpenEMR patient id                                            |
| `created_at`         | `DateTime(timezone=True)` | no       | Created timestamp (UTC)                                       |

### `clinical_note_records` (`ClinicalNoteRecord`)

| Column                  | Type                      | Required | Notes                                                         |
| ----------------------- | ------------------------- | -------- | ------------------------------------------------------------- |
| `id`                    | `Integer`                 | yes      | Primary key                                                   |
| `zoom_meeting_id`       | `String(128, FK)`         | yes      | FK to `meeting_records.zoom_meeting_id` (`ON DELETE CASCADE`) |
| `zoom_note_id`          | `String(128)`             | yes      | Zoom note identifier (unique)                                 |
| `zoom_note_title`       | `String(256)`             | no       | Note title                                                    |
| `note_content`          | `Text`                    | no       | Note body                                                     |
| `received_at`           | `DateTime(timezone=True)` | no       | Receipt timestamp                                             |
| `written_to_openemr_at` | `DateTime(timezone=True)` | no       | OpenEMR write timestamp                                       |
| `completed_in_zoom_at`  | `DateTime(timezone=True)` | no       | Zoom completion timestamp                                     |
| `is_written_to_openemr` | `Boolean`                 | yes      | Write success marker                                          |
| `is_completed_in_zoom`  | `Boolean`                 | yes      | Completion success marker                                     |
| `error_message`         | `Text`                    | no       | Error details                                                 |

### `audit_log` (`AuditLog`)

| Column                     | Type                      | Required | Notes                  |
| -------------------------- | ------------------------- | -------- | ---------------------- |
| `id`                       | `Integer`                 | yes      | Primary key            |
| `event_type`               | `String(128)`             | yes      | Event category         |
| `zoom_account_id`          | `String(128)`             | no       | Context field          |
| `openemr_appointment_id`   | `String(128)`             | no       | Context field          |
| `openemr_encounter_number` | `String(128)`             | no       | Context field          |
| `openemr_provider_id`      | `String(128)`             | no       | Context field          |
| `openemr_patient_id`       | `String(128)`             | no       | Context field          |
| `zoom_meeting_id`          | `String(128)`             | no       | Context field          |
| `zoom_note_id`             | `String(128)`             | no       | Context field          |
| `success`                  | `Boolean`                 | no       | Outcome marker         |
| `error_message`            | `Text`                    | no       | Error detail           |
| `detail`                   | `Text`                    | no       | Extra JSON/detail blob |
| `occurred_at`              | `DateTime(timezone=True)` | yes      | Event timestamp        |

## Admin API Auth Contract

The React config UI authenticates through `POST /api/auth/login`:

- Request body: `{"password": "..."}`
- Password is compared against `CONFIG_ADMIN_PASSWORD`
- Successful login returns an HS256 JWT signed with `CONFIG_JWT_SECRET`
- Token payload uses `sub = admin` and a 12-hour expiration

`GET /api/auth/verify` validates the same bearer token and returns `{"ok": true}` when valid.

Protected blueprints require:

```http
Authorization: Bearer <jwt>
```

JWT-protected blueprints:

- `/config/*`
- `/openemr/*`
- `/zoom/*`, except OpenEMR-signed note endpoints
- `/audit/*`

Webhook routes keep their own signature contracts and do not use the config JWT.

## Registration API Contract

`POST /config/register` creates a Zoom account registration.

Required JSON fields:

- `zoom_account_id`
- `zoom_client_id`
- `zoom_client_secret`
- `zoom_webhook_secret`
- `contact_email`

Optional JSON fields:

- `nickname`
- `timezone` (defaults to `America/New_York`)
- `ehr_context_username`
- `ehr_context_password`

Registration returns the saved `ZoomAccount` identity fields plus the created `AccountConfig.timezone` and default `AccountConfig.note_writeback_mode`. EHR Context credentials are stored on `ZoomAccount`; timezone, note writeback mode, shared-user behavior, and demo override settings are stored on `AccountConfig`.

The registration flow auto-enables the dynamically registered OpenEMR client. After the RFC 7591 registration succeeds, Flask runs `UPDATE oauth_clients SET is_enabled = 1 WHERE client_id = :client_id` against the OpenEMR database. This removes the manual "Enable Client" step from the SE demo flow.

Rollback fires on either of two failure modes so the OpenEMR side never ends up with an enabled-but-orphaned client:

- **Auto-enable failure** (UPDATE raises, or matches 0 rows): registration aborts; the OpenEMR client is deregistered via the RFC 7591 management URI and the local keypair is deleted. Surfaced by `openemr.client_enabled` (success) / `openemr.client_enable_failed` (raises) audit events.
- **Flask DB-persist failure** (commit on the `ZoomAccount` / `AccountConfig` rows raises): same cleanup chain — `_deregister_from_openemr` + `delete_keypair` — so the (already-enabled) OpenEMR client doesn't outlive a Flask account that never persisted.

`_deregister_from_openemr` swallows its own errors, so a simultaneously-unavailable OpenEMR during cleanup never compounds the original failure.

`PATCH /config/register/<zoom_account_id>` updates editable registration and account config fields. Only fields sent with non-null values are updated; `false` is valid for boolean settings.

Editable JSON fields:

- `nickname`
- `zoom_client_secret`
- `zoom_webhook_secret`
- `ehr_context_username`
- `ehr_context_password`
- `timezone`
- `allow_shared_zoom_user`
- `demo_patient_email_override_enabled`
- `demo_patient_email_override`
- `demo_patient_phone_override_enabled`
- `demo_patient_phone_override`
- `note_writeback_mode` (`both`, `clinical_note_only`, or `soap_only`)

`GET /config/registrations` includes `nickname`, `tenant_id`, EHR Context username, token status, `AccountConfig.timezone`, `allow_shared_zoom_user`, and the split demo patient contact override flags/values in each registration summary. `POST /config/register/<zoom_account_id>/verify` includes `nickname`, OpenEMR verification, Zoom verification, and a combined status message.

## Lookup And Audit API Contracts

JWT-protected lookup helpers:

- `GET /openemr/providers?zoom_account_id=...&search=...&id=...`
- `GET /openemr/appointment-types?zoom_account_id=...`
- `GET /zoom/users?zoom_account_id=...&search=...`

All three require an active `ZoomAccount` for the supplied `zoom_account_id`. OpenEMR provider responses include `user_id`, the OpenEMR `users.id` value that should be stored on `ProviderMapping.openemr_provider_id` for webhook matching and EHR Context appointment lookups.

JWT-protected audit log endpoint:

- `GET /audit/logs`

Supported filters:

- `zoom_account_id`
- `event_type`
- `openemr_appointment_id`
- `openemr_encounter_number`
- `openemr_provider_id`
- `openemr_patient_id`
- `zoom_meeting_id`
- `zoom_note_id`
- `success` (`true` or `false`)
- `date_from` / `date_to` ISO datetimes
- `page` / `per_page` pagination (`per_page` max 200)

Response shape:

```json
{
  "total": 1,
  "page": 1,
  "per_page": 50,
  "pages": 1,
  "logs": []
}
```

## Zoom EHR Context API Contract

These `/rest/*` routes are called by Zoom's EHR integration and are not config-JWT protected.

> **Gotcha:** The endpoint URLs configured on the Zoom Marketplace app's
> EHR Context tab must have no leading or trailing whitespace. Zoom silently
> drops the call (no webhook history entry on Zoom's side, no inbound request
> on Flask's side) if the URL has a stray space — a particularly hard failure
> to diagnose because Postman against the same URL works fine. If a session
> doesn't trigger `gettoken` even though identical config works for another
> account, character-by-character compare the URL fields first.

`GET /rest/auth/gettoken`

- Requires `X-Tenant-ID: <tenant_id>`
- Requires Basic Auth credentials matching `ZoomAccount.ehr_context_username` and `ehr_context_password_hash`
- Returns `{"token": "...", "token_type": "Bearer", "expires_in": 3600}`
- Token is an HS256 JWT signed with Flask `SECRET_KEY` and includes `sub` and `tid` claims set to the tenant ID

`POST /rest/openendpoint/service/getAppointments`

- Requires the same `X-Tenant-ID`
- Requires `Authorization: Bearer <token-from-gettoken>`
- Body: `{"dateTime": "2026-04-27T16:00:00", "zoomUserId": "..."}` where `dateTime` is UTC
- Resolves `zoomUserId` through `ProviderMapping.zoom_user_id`
- Requires `ProviderMapping.openemr_provider_id`
- Converts the UTC query time into `AccountConfig.timezone`, queries OpenEMR appointments within +/- 2 hours, and returns Zoom's expected appointment list wrapper:

```json
{
  "status": 200,
  "response": [
    {
      "appointmentId": "391",
      "providerId": "10",
      "patientId": "109",
      "startTime": "2026-04-27T16:00:00Z",
      "endTime": "2026-04-27T16:30:00Z",
      "serviceType": "Zoom Telehealth",
      "name": "Aisha Johnson",
      "dob": "1993-01-25",
      "gender": "Female",
      "appointmentType": "Telehealth Zoom"
    }
  ]
}
```

## OpenEMR Appointment Webhook Contract

OpenEMR listener sends JSON payloads to `POST /webhooks/openemr` signed with:

- Header `X-Zoomly-Signature`
- Value `hex(hmac_sha256(raw_body, OPENEMR_FLASK_SECRET))`

`appointment.set` payload fields:

- `event` (`appointment.set`)
- `eid`
- `pid`
- `provider_id`
- `category_id`
- `appointment_date`
- `appointment_time`
- `duration_minutes`
- `appt_status`
- `facility_id`
- `title`
- `room`
- `comments`
- `fired_at`

`appointment.deleted` payload fields:

- `event` (`appointment.deleted`)
- `eid`
- `fired_at`

Current bridge behavior:

- Validates signature and minimal payload shape
- For `appointment.set`:
  - filters by `ProviderMapping.openemr_provider_id` and appointment-type allowlist
  - creates new meetings when no `MeetingRecord` exists
  - updates existing meetings when `MeetingRecord` exists and Zoom meeting is still present
  - recreates meetings when `MeetingRecord` exists but Zoom meeting was deleted
  - writes meeting links back to OpenEMR appointment row:
    - `pc_website` = `<start_url>`
  - writes `MeetingRecord` and `MeetingPatient` rows
  - returns one of: `ok`, `partial`, `error`, `dropped`
- For `appointment.deleted`:
  - finds `MeetingRecord` rows by `eid`
  - deletes Zoom meetings
  - branches on local state: removes the `MeetingRecord` (cascade clears `MeetingPatient` rows) when no `ClinicalNoteRecord` exists, or preserves the row with `status="cancelled"` when a `ClinicalNoteRecord` exists so the chart-data audit trail is retained
  - returns one of: `deleted`, `no_record`, `error`

Audit event taxonomy is canonical in the `write_audit_log()` docstring at `server/app/services/audit.py` — read that before adding or referencing event types. As of Sprint 7 cleanup, coverage spans appointment lifecycle, meeting lifecycle, clinical-note pipeline (async + manual fetch), encounter create/claim, and Zoom completion outcomes. Categories at a glance:

- `appointment.*` — webhook receipt, drop reasons (`detail.reason` of `missing_provider_id`, `provider_unmapped`, `account_inactive`, `type_mismatch`), patient arrival, delete-no-record
- `meeting.*` — create/update/recreate/delete success and failure, `meeting.started`, `meeting.cancelled` (appointment deleted but local row preserved because a `ClinicalNoteRecord` exists; `detail.preserved=True`, `detail.reason="clinical_note_present"`)
- `openemr.url_writeback_*` — appointment URL writeback outcomes
- `note.*` — receipt, async scheduling, content fetch (including `note.fetched_after_retry`, `note.content_empty`, `note.fetch_error`), record creation, write success/failure, drop/context-missing paths, async safety nets (`note.handler_error`, `note.async_job_error`), and manual fetch (`note.manual_fetch_requested`, `note.manual_fetch_failed` with `detail.reason`)
- `encounter.*` — `encounter.created` (with `detail.trigger`), `encounter.create_failed`, `encounter.claimed` (manual-fallback match path, S7-01)
- `zoom.completion_*` — completion success, skipped (idempotent), error
- `zoom.webhook_signature_failed` — Zoom HMAC mismatch
- `jwks.fetched` — `/.well-known/jwks.json` endpoint hit; `detail.client_ip`, `detail.active_accounts`, `detail.keys_served`. Useful for diagnosing OpenEMR JWKS cache behavior (S7-08)
- `openemr.token_refresh_failed` — `get_openemr_token` failure; HTTPError carries `detail.status_code`, `detail.oauth_error`, `detail.body_snippet`; otherwise `detail.stage="network"` or `"assertion"`. Pairs with `openemr.token_verify_failed` on the UI verify path
- `openemr.token_verify_*` — UI verify endpoint outcomes (`success` / `failed`). `failed` carries `detail.status_code` on HTTPError or `detail.stage="unexpected"` otherwise
- `zoom.token_refresh_failed` — `_fetch_zoom_token` failure; HTTPError carries `detail.status_code`, `detail.zoom_error`, `detail.body_snippet`; otherwise `detail.stage="network"` or `"fetch"`. Pairs with `zoom.credentials_validation_failed` on the registration path
- `zoom.credentials_*` — registration-time validation outcomes (`validated` with `detail.scopes` / `validation_failed` with `detail.status_code`)
- `zoom.webhook_account_mismatch` — payload account_id didn't match the URL path account_id on a per-account webhook (`/webhooks/zoom/<account_id>`)
- `demo.*` — Hydrate Demo Data orchestrator and past-encounter seeder events (Sprint 13): `hydrate_started`, `hydrate_completed`, `hydrate_request_failed`, `hydrate_provider_skipped` (with `detail.reason`), `future_appointment_created`, `future_appointment_create_failed`, `future_meeting_created`, `future_meeting_backfilled`, `past_encounter_seeded`, `past_encounter_skipped` (with `detail.reason`), `past_encounter_failed` (with `detail.stage`). Full taxonomy + detail field shapes in `services/audit.py`.

`note.written` and `note.write_failed` include `openemr_encounter_number` and `detail.content_blank`; manual-fetch flows carry `detail.trigger=manual_fetch`.

## Zoom Webhook Contract

Zoom sends signed webhook payloads to `POST /webhooks/zoom`.

Current supported Zoom events:

- `endpoint.url_validation` returns Zoom's CRC `plainToken` / `encryptedToken` response
- `clinical_notes.note_created` records note receipt and schedules an immediate async fetch (delay=0). If Zoom serves empty content on the first read, the fetcher retries up to 3 times with 15s between attempts (handles a historical Zoom bug that has since been resolved but the retry stays in place as a safety net). Writes to OpenEMR using `AccountConfig.note_writeback_mode`.
- `meeting.started` marks the `MeetingRecord` as `started`, stamps `meeting_started_at`, and helps EHR Context resolve shared Zoom user mappings. Also flips the OpenEMR appointment to In Exam Room (`<`).
- `meeting.ended` flips the OpenEMR appointment to Checked Out (`>`).
- `meeting.participant_jbh_waiting` is the patient-arrived signal — fires when a participant clicks the join URL before the host starts the meeting. Updates the OpenEMR appointment status to Arrived (`@`) and attempts encounter creation. `meeting.participant_joined_waiting_room` is also handled by the dispatcher as a defensive fallback. Slated for cleanup after more demo testing.

Manual note endpoints under `/zoom/encounter/<encounter_number>/...` are OpenEMR-signed, JWT-exempt routes:

- `fetch_zoom_note` resolves a `note_id` via `MeetingRecord.clinical_note.zoom_note_id`. When multiple `ClinicalNoteRecord` rows exist for one meeting (e.g. a failed/empty note followed by a real one), the relationship returns the most-recently-received note (`order_by="ClinicalNoteRecord.received_at.desc()"`). Form dedup is encounter-scoped, so repeated retrieves on the same encounter update the existing SOAP + Clinical Notes forms in place. **Limitation:** recurring Zoom meetings that share a `zoom_meeting_id` across multiple appointments are not yet supported — the schema forces 1 MeetingRecord per Zoom meeting. Tracked as TD-01 in `phase-2-sprint-plan.md`.
- `complete_zoom_note` marks the stored Zoom note complete; the route is idempotent and returns 200 for valid skip/error outcomes so OpenEMR UI actions are not blocked

## OpenEMR Patch Module (PHP)

Patch files under `patches/zoom_appointment_listener` currently wire two events:

- `AppointmentSetEvent` -> `AppointmentListener::onAppointmentSet` for create/update webhook payloads
- `AppointmentDialogCloseEvent` -> `DialogCloseListener::onDialogClose` for delete webhook payloads

Patch files under `patches/clinical_note_fetcher` provide OpenEMR encounter-page proxies:

- `fetch_zoom_note.php` signs and forwards "Retrieve Zoom Note" requests to Flask
- `complete_zoom_note.php` signs and forwards Zoom note completion requests; the JavaScript trigger in `forms.php` is currently present but commented out
- `forms.php` contains the encounter-page "Retrieve Zoom Note" button integration

Current listener behavior highlights:

- Drops all-day events early (`form_allday = 1`)
- Sends `duration_minutes`, `title`, and `room` in `appointment.set`
- Sends compact `appointment.deleted` payload for delete actions
- Signs all webhook payloads with HMAC-SHA256 using `OPENEMR_FLASK_SECRET`

`patches/RsaSha384Signer.php` overrides `src/Common/Auth/OpenIDConnect/JWT/RsaSha384Signer.php` to fix a multi-client JWT verification bug (S7-08). Upstream's `verify()` reads kid from `$this->headers['kid']`, which is only populated during signing — during verification kid was always null, causing `JsonWebKeySet::getJSONWebKey()` to return the first RSA key in the JWKS regardless of which client's token was being validated. The patch extracts kid from the JWT header bytes in `$payload` (the signed segment Lcobucci passes into `verify()`). Bind-mounted `:ro` so OpenEMR's auto-config can't overwrite it.

## OpenEMR Appointment Status (`appt_status`) Mapping

These are the internal integration meanings we are targeting:

| Code | Label          | Intended integration behavior                         |
| ---- | -------------- | ----------------------------------------------------- |
| `^`  | Pending        | Appointment created; meeting should exist/be prepared |
| `@`  | Arrived        | Patient arrived; keep meeting active                  |
| `<`  | In exam room   | Rooming started; alternative host logic most relevant |
| `>`  | Checked out    | Visit complete; closeout/completion workflow          |
| `x`  | Canceled       | Cancel appointment; delete/cleanup Zoom meeting       |
| `%`  | Canceled < 24h | Cancel appointment; delete/cleanup Zoom meeting       |
| `?`  | No show        | Patient did not arrive; no-show cleanup flow          |

Important: OpenEMR option codes are configurable per deployment.  
Verify your actual status codes in your OpenEMR DB:

```sql
SELECT option_id, title, seq
FROM list_options
WHERE list_id = 'apptstat' AND activity = 1
ORDER BY seq;
```

## Migration Notes

Current migration chain:

- `0d3e2936f4b1_initial_schema` (baseline/stamp)
- `5ecd2a942ca3_current_schema_with_string_primary_keys`
- `77ba73f9eedb_add_account_config_table_move_config_`
- `d7de11bd0c97_split_demo_patient_override_enabled_`
- `585c85c5c79c_add_ehr_auth_fields_to_zoom_accounts`
- `18c6821766b3_add_meeting_started_at_to_meeting_`
- `8e1a97239ec2_add_note_writeback_mode_to_account_`

The current schema migration uses natural string primary keys for the core integration relationships:

- `zoom_accounts.account_id`
- `meeting_records.zoom_meeting_id`
- foreign keys from provider mappings, appointment filters, meeting records, patients, and clinical notes point at those natural IDs.

Recent config/auth migrations:

- move per-account scheduling/demo settings from `zoom_accounts` to `account_configs`
- split the old single demo patient override flag into separate email and phone enabled flags
- add EHR Context tenant ID, username, and password hash fields to `zoom_accounts`
- add the unique `zoom_accounts.tenant_id` index and nullable `meeting_records.meeting_started_at`
- add `account_configs.note_writeback_mode` with default `both`

## Test Coverage Pointers

Primary files for this integration slice:

- `server/tests/test_blueprint_audit.py`
- `server/tests/test_blueprint_auth.py`
- `server/tests/test_blueprint_webhooks.py`
- `server/tests/test_blueprint_ehr_context.py`
- `server/tests/test_blueprint_openemr.py`
- `server/tests/test_blueprint_zoom.py`
- `server/tests/test_zoom_webhook_audit.py`
- `server/tests/test_services_appointment_processor.py`
- `server/tests/test_services_appointment_filters.py`
- `server/tests/test_services_audit.py`
- `server/tests/test_services_openemr.py`
- `server/tests/test_services_openemr_note.py`
- `server/tests/test_services_providers.py`
- `server/tests/test_services_keys.py`
- `server/tests/test_services_registration.py`
- `server/tests/test_services_reg_verification.py`
- `server/tests/test_services_zoom.py`
- `server/tests/test_blueprint_config.py`
- `server/tests/test_jwks.py`
- `server/tests/test_jwt_assertion.py`
- `server/tests/test_routes.py`
- `server/tests/test_seed_data_sql.py`
- `server/tests/test_migration_timezone.py`
- `server/tests/test_migration_meeting_records.py`
- `server/tests/test_migration_provider_mappings.py`
- `server/tests/test_migration_demo_patient_overrides.py`
- `server/tests/test_migration_zoom_account_registration_updates.py`
- `server/tests/test_patch_zoom_listener_module.py`

# Zoomly Internal Integration Reference

Internal developer notes for the Zoom <-> OpenEMR bridge.  
This is a working reference for model contracts, webhook payload expectations, and integration-specific code mappings.

## Data Models

### `zoom_accounts` (`ZoomAccount`)

| Column | Type | Required | Notes |
|---|---|---|---|
| `account_id` | `String(128)` | yes | Zoom account-level identifier, primary key |
| `key_version` | `Integer` | yes | Encryption key version used for row-level secrets |
| `nickname` | `String(128)` | no | Optional display name for the registration/config UI |
| `client_id` | `String(128)` | yes | Zoom OAuth client ID |
| `client_secret` | `EncryptedType(String(256))` | yes | Zoom OAuth client secret (encrypted at rest) |
| `webhook_secret` | `EncryptedType(String(256))` | no | Zoom webhook secret (encrypted at rest) |
| `zoom_access_token` | `EncryptedType(Text)` | no | Cached Zoom token (encrypted at rest) |
| `zoom_token_expires_at` | `DateTime(timezone=True)` | no | Zoom token expiry |
| `openemr_client_id` | `String(256)` | no | Dynamic registration client ID from OpenEMR |
| `openemr_client_secret` | `EncryptedType(String(256))` | no | OpenEMR dynamic registration client secret (encrypted at rest) |
| `openemr_registration_access_token` | `EncryptedType(Text)` | no | Registration management token (encrypted at rest) |
| `openemr_registration_client_uri` | `String(512)` | no | Registration management URI |
| `openemr_access_token` | `EncryptedType(Text)` | no | Cached OpenEMR access token (encrypted at rest) |
| `openemr_token_expires_at` | `DateTime(timezone=True)` | no | OpenEMR token expiry |
| `private_key_path` | `String(512)` | no | Filesystem path to per-account private key |
| `kid` | `String(256)` | no | JWKS key id used for private_key_jwt |
| `timezone` | `String(64)` | yes | IANA timezone; default `America/New_York` |
| `demo_patient_override_enabled` | `Boolean` | yes | Enables use of demo patient contact overrides |
| `demo_patient_email_override` | `String(256)` | no | Optional demo override for patient email communications |
| `demo_patient_phone_override` | `String(32)` | no | Optional demo override for patient phone/SMS communications |
| `is_active` | `Boolean` | yes | Soft-active registration state |
| `created_at` | `DateTime(timezone=True)` | yes | Created timestamp (UTC) |
| `updated_at` | `DateTime(timezone=True)` | yes | Updated timestamp (UTC) |

Relationships:
- `provider_mappings` -> `ProviderMapping[]`
- `appointment_type_filters` -> `AppointmentTypeFilter[]`
- `meeting_records` -> `MeetingRecord[]`

### `provider_mappings` (`ProviderMapping`)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | `Integer` | yes | Primary key |
| `zoom_account_id` | `String(128, FK)` | yes | FK to `zoom_accounts.account_id` |
| `openemr_fhir_id` | `String(128)` | yes | OpenEMR practitioner FHIR id |
| `openemr_provider_npi` | `String(10)` | yes | Provider NPI used by filter pipeline |
| `openemr_provider_id` | `String(128)` | no | OpenEMR `users.id` / appointment `provider_id` used for webhook matching |
| `openemr_provider_name` | `String(256)` | no | Provider display name |
| `zoom_user_email` | `String(256)` | yes | Zoom host email |
| `zoom_user_name` | `String(256)` | no | Zoom display name |
| `zoom_user_id` | `String(128)` | no | Zoom user id |
| `zoom_user_type` | `Integer` | no | Zoom license/type |
| `default_alternative_host_email` | `String(256)` | no | Default alternative host |
| `is_active` | `Boolean` | yes | Active mapping flag |
| `created_at` | `DateTime(timezone=True)` | no | Created timestamp (UTC) |

### `appointment_type_filters` (`AppointmentTypeFilter`)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | `Integer` | yes | Primary key |
| `zoom_account_id` | `String(128, FK)` | yes | FK to `zoom_accounts.account_id` |
| `openemr_type_id` | `String(128)` | yes | OpenEMR appointment category/list option id |
| `openemr_type_name` | `String(256)` | yes | OpenEMR appointment category/list option display name |
| `created_at` | `DateTime(timezone=True)` | no | Created timestamp (UTC) |

### `meeting_records` (`MeetingRecord`)

| Column | Type | Required | Notes |
|---|---|---|---|
| `zoom_meeting_id` | `String(128)` | yes | Zoom meeting ID, primary key |
| `zoom_account_id` | `String(128, FK)` | yes | FK to `zoom_accounts.account_id` |
| `zoom_start_url` | `String(1024)` | no | Host/alt-host start URL |
| `zoom_join_url` | `String(1024)` | no | Patient join URL |
| `alternative_host_email` | `String(256)` | no | Captured alternative host |
| `openemr_appointment_id` | `String(128)` | yes | OpenEMR appointment/event id |
| `openemr_provider_id` | `String(128)` | yes | OpenEMR provider id (`users.id`) |
| `openemr_appt_status` | `String(16)` | no | OpenEMR `apptstat`/`pc_apptstatus` code |
| `status` | `String(64)` | yes | Internal progression status (for workflow orchestration) |
| `created_at` | `DateTime(timezone=True)` | no | Created timestamp (UTC) |
| `updated_at` | `DateTime(timezone=True)` | no | Updated timestamp (UTC) |

Relationships:
- `patients` -> `MeetingPatient[]`
- `clinical_note` -> `ClinicalNoteRecord | None`

### `meeting_patients` (`MeetingPatient`)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | `Integer` | yes | Primary key |
| `zoom_meeting_id` | `String(128, FK)` | yes | FK to `meeting_records.zoom_meeting_id` (`ON DELETE CASCADE`) |
| `openemr_patient_id` | `String(128)` | yes | OpenEMR patient id |
| `created_at` | `DateTime(timezone=True)` | no | Created timestamp (UTC) |

### `clinical_note_records` (`ClinicalNoteRecord`)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | `Integer` | yes | Primary key |
| `zoom_meeting_id` | `String(128, FK)` | yes | FK to `meeting_records.zoom_meeting_id` |
| `zoom_note_id` | `String(128)` | yes | Zoom note identifier (unique) |
| `zoom_note_title` | `String(256)` | no | Note title |
| `note_content` | `Text` | no | Note body |
| `received_at` | `DateTime(timezone=True)` | no | Receipt timestamp |
| `written_to_openemr_at` | `DateTime(timezone=True)` | no | OpenEMR write timestamp |
| `completed_in_zoom_at` | `DateTime(timezone=True)` | no | Zoom completion timestamp |
| `is_written_to_openemr` | `Boolean` | yes | Write success marker |
| `is_completed_in_zoom` | `Boolean` | yes | Completion success marker |
| `error_message` | `Text` | no | Error details |

### `audit_log` (`AuditLog`)

| Column | Type | Required | Notes |
|---|---|---|---|
| `id` | `Integer` | yes | Primary key |
| `event_type` | `String(128)` | yes | Event category |
| `zoom_account_id` | `String(128)` | no | Context field |
| `openemr_appointment_id` | `String(128)` | no | Context field |
| `openemr_provider_id` | `String(128)` | no | Context field |
| `openemr_patient_id` | `String(128)` | no | Context field |
| `zoom_meeting_id` | `String(128)` | no | Context field |
| `zoom_note_id` | `String(128)` | no | Context field |
| `success` | `Boolean` | no | Outcome marker |
| `error_message` | `Text` | no | Error detail |
| `detail` | `Text` | no | Extra JSON/detail blob |
| `occurred_at` | `DateTime(timezone=True)` | yes | Event timestamp |

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

`PATCH /config/register/<zoom_account_id>` updates editable registration fields. Only fields sent with non-null values are updated; `false` is valid for `demo_patient_override_enabled`.

Editable JSON fields:
- `nickname`
- `zoom_client_secret`
- `zoom_webhook_secret`
- `timezone`
- `demo_patient_override_enabled`
- `demo_patient_email_override`
- `demo_patient_phone_override`

`GET /config/registrations` includes `nickname`, `demo_patient_override_enabled`, and the demo patient contact override values in each registration summary. `POST /config/register/<zoom_account_id>/verify` includes `nickname` in its response.

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
  - removes local meeting records (cascade removes meeting-patient rows)
  - returns one of: `deleted`, `no_record`, `error`

Audit events emitted by webhook handlers:
- `appointment.received.<event>` on accepted inbound payloads
- `appointment.dropped` when filtering produces no account/provider/type matches
- `meeting.created`, `meeting.updated`, `meeting.recreated`, `meeting.deleted` on successful meeting lifecycle actions
- `meeting.create_failed`, `meeting.delete_failed` on handled failure paths
- `openemr.url_writeback_success`, `openemr.url_writeback_failed` for appointment URL writeback outcomes

## OpenEMR Patch Module (PHP)

Patch files under `patches/zoom_appointment_listener` currently wire two events:
- `AppointmentSetEvent` -> `AppointmentListener::onAppointmentSet` for create/update webhook payloads
- `AppointmentDialogCloseEvent` -> `DialogCloseListener::onDialogClose` for delete webhook payloads

Current listener behavior highlights:
- Drops all-day events early (`form_allday = 1`)
- Sends `duration_minutes`, `title`, and `room` in `appointment.set`
- Sends compact `appointment.deleted` payload for delete actions
- Signs all webhook payloads with HMAC-SHA256 using `OPENEMR_FLASK_SECRET`

## OpenEMR Appointment Status (`appt_status`) Mapping

These are the internal integration meanings we are targeting:

| Code | Label | Intended integration behavior |
|---|---|---|
| `^` | Pending | Appointment created; meeting should exist/be prepared |
| `@` | Arrived | Patient arrived; keep meeting active |
| `<` | In exam room | Rooming started; alternative host logic most relevant |
| `>` | Checked out | Visit complete; closeout/completion workflow |
| `x` | Canceled | Cancel appointment; delete/cleanup Zoom meeting |
| `%` | Canceled < 24h | Cancel appointment; delete/cleanup Zoom meeting |
| `?` | No show | Patient did not arrive; no-show cleanup flow |

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

The current schema migration uses natural string primary keys for the core integration relationships:
- `zoom_accounts.account_id`
- `meeting_records.zoom_meeting_id`
- foreign keys from provider mappings, appointment filters, meeting records, patients, and clinical notes point at those natural IDs.

## Test Coverage Pointers

Primary files for this integration slice:
- `server/tests/test_blueprint_auth.py`
- `server/tests/test_blueprint_webhooks.py`
- `server/tests/test_blueprint_openemr.py`
- `server/tests/test_blueprint_zoom.py`
- `server/tests/test_services_appointment_processor.py`
- `server/tests/test_services_appointment_filters.py`
- `server/tests/test_services_audit.py`
- `server/tests/test_services_openemr.py`
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

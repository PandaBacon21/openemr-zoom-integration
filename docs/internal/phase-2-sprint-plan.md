# Phase 2 Sprint Plan

This is a future-facing planning reference for Phase 2 work. Status, size, priority, and notes mirror the source planning sheet; it is not a statement that the backlog items are currently implemented.

## Sprint 7 - Stabilization And Staging Readiness

| ID    | Area           | Size | Status  | Priority | Story / Task                                   | Notes                                                                                                                                                                                                      |
| ----- | -------------- | ---: | ------- | -------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S7-01 | Flask Backend  |    S | Backlog | High     | Manual arrival duplicate encounter fix         | Re-add a guarded `external_id IS NULL` fallback to `find_encounter_for_appointment()` to prevent a second encounter when a provider manually sets Arrived instead of the patient joining the waiting room. |
| S7-02 | Flask Backend  |    S | Backlog | Medium   | `AppointmentTypeFilter.zoom_account_id` FK fix | Ensure the FK references `ZoomAccount.account_id` as a string primary key after the Sprint 6 schema refactor.                                                                                              |
| S7-03 | Flask Backend  |    M | Backlog | High     | Note writeback mode bug                        | Investigate and fix `write_note_to_encounter()` skipping SOAP when mode is `both`; suspected lazy-load/default issue in the background job context.                                                        |
| S7-04 | Flask Backend  |    S | Backlog | High     | `_fetch_note_with_retry` HTTPError handling    | Wrap `get_zoom_clinical_note` in try/except so Zoom API 400/500 responses do not crash the APScheduler job.                                                                                                |
| S7-05 | Flask Backend  |    M | Backlog | High     | Redesign OpenEMR verify flow                   | Stop using forced token acquisition as the proxy for client-enabled status; research `registration_client_uri` GET or `oauth_clients` query.                                                               |
| S7-06 | React Frontend |    S | Backlog | High     | `runVerify` race condition                     | Add a last-checked account guard so stale async verify responses cannot overwrite state after switching accounts.                                                                                          |
| S7-07 | Flask Backend  |    S | Backlog | Medium   | Stop token minting on every verify poll        | Use cached tokens in the background polling loop; only force refresh on manual re-verify.                                                                                                                  |
| S7-08 | Flask Backend  |    M | Backlog | High     | Multi-account JWKS caching fix                 | OpenEMR caches `/.well-known/jwks.json`; fix cache busting on new registration or evaluate inline JWKS on `oauth_clients`.                                                                                 |
| S7-09 | Infrastructure |    S | Backlog | Medium   | `docker-compose.staging.yml` overlay           | Extend OpenEMR healthcheck `start_period` to 15 minutes and adjust startup dependencies for staging.                                                                                                       |
| S7-10 | Infrastructure |    S | Backlog | Medium   | `start-staging.sh`                             | Wrap staging compose startup, post-start chmod for `ZoomBridge.php`, and Alembic migration commands.                                                                                                       |
| S7-11 | Flask Backend  |    S | Done    | High     | Tenant ID exposure                             | `tenant_id` was added to `GET /config/registrations` and displayed in `CredentialsSection.tsx`.                                                                                                            |
| S7-12 | QA             |    M | Backlog | High     | End-to-end staging regression                  | Exercise appointment -> waiting room -> meeting started -> note created -> SOAP and clinical note writeback; verify both accounts resolve correctly.                                                       |

## Sprint 8 - Internal Database Access

| ID    | Area           | Size | Status  | Priority | Story / Task                     | Notes                                                                                                  |
| ----- | -------------- | ---: | ------- | -------- | -------------------------------- | ------------------------------------------------------------------------------------------------------ |
| S8-01 | Infrastructure |    S | Backlog | High     | Add Adminer Docker service       | Internal-only `adminer:latest`, no NPM exposure; connect to both `mariadb-emr` and `zoomly-postgres`.  |
| S8-02 | React Frontend |    S | Backlog | High     | Adminer nav item                 | Add an admin-only Database nav item that renders Adminer in a full-height iframe through Flask.        |
| S8-03 | Flask Backend  |    S | Backlog | Medium   | Adminer reverse proxy            | Add JWT-protected `/admin/db` proxy to `http://adminer:8080` so Adminer stays off the public internet. |
| S8-04 | QA             |    S | Backlog | Medium   | Validate Adminer database access | Verify browsing and read/write operations for both OpenEMR MariaDB and Zoomly PostgreSQL schemas.      |

## Sprint 9 - SE Demo Completion

| ID    | Area          | Size | Status  | Priority | Story / Task                             | Notes                                                                                                                            |
| ----- | ------------- | ---: | ------- | -------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| S9-01 | QA            |    L | Backlog | High     | SE demo run-through                      | SE testers can run the full telehealth demo workflow independently; document friction points.                                    |
| S9-02 | OpenEMR       |    M | Backlog | High     | Wire `complete_zoom_note` to eSign event | Re-wire eSign event in `forms.php`; use `window.location.origin` prefix on the fetch call to avoid redirect issues.              |
| S9-03 | Flask Backend |    M | Backlog | Medium   | Locked/eSigned encounter guard           | Query `esign_signatures` before SOAP and clinical note upserts; skip locked encounters gracefully with audit context.            |
| S9-04 | QA            |    M | Backlog | Medium   | Demo script documentation                | Create a step-by-step SE walkthrough with screenshots for scheduling, waiting room, meeting start, clinical note, and writeback. |

## Sprint 10 - Epic-Style OpenEMR Skin And Custom Image

| ID     | Area           | Size | Status  | Priority | Story / Task                           | Notes                                                                                                              |
| ------ | -------------- | ---: | ------- | -------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| S10-01 | Research       |    M | Backlog | High     | Research Epic EHR UI patterns          | Document patient banner, left nav, chart sidebar, top toolbar, color palette, and layout conventions.              |
| S10-02 | Infrastructure |    L | Backlog | High     | Custom OpenEMR Docker image foundation | Build from `openemr/openemr:8.0.0` with PHP patches, branding assets, and `ZoomBridge.php` baked in; host on GHCR. |
| S10-03 | Infrastructure |    M | Backlog | Medium   | GitHub Actions image pipeline          | Build and push the custom OpenEMR image to GHCR on merge to `main`; update compose to pull from GHCR.              |
| S10-04 | OpenEMR        |    L | Backlog | High     | Epic-style patient banner              | Override patient header with patient name, DOB/age/sex, MRN, allergies, and insurance summary.                     |
| S10-05 | OpenEMR        |    L | Backlog | High     | Epic-style left navigation             | Convert horizontal top navigation into a persistent left rail with chart modules and active state.                 |
| S10-06 | OpenEMR        |    L | Backlog | High     | Epic-style chart sidebar               | Split encounter/chart view into chronological encounter list plus selected encounter content.                      |
| S10-07 | OpenEMR        |    M | Backlog | Medium   | Epic color palette and typography      | Add global CSS for dark navy rail, white content area, teal accents, gray table rows, and utilitarian type.        |
| S10-08 | OpenEMR        |    M | Backlog | Medium   | Epic-style top toolbar                 | Add patient search, user context, and notifications; remove OpenEMR-specific branding elements.                    |
| S10-09 | QA             |    M | Backlog | Medium   | End-to-end visual QA                   | Walk the full demo flow in the Epic-skinned OpenEMR and check cross-page layout behavior.                          |

## Sprint 11 - ZCC CTI Screen Pop

| ID     | Area           | Size | Status  | Priority | Story / Task                                | Notes                                                                                                               |
| ------ | -------------- | ---: | ------- | -------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| S11-01 | Research       |    M | Backlog | High     | Research ZCC Smart Embed and screen pop API | Document ZCC caller context delivery, payload structure, trigger timing, and Smart Embed iframe/deep-link APIs.     |
| S11-02 | Database       |    M | Backlog | High     | `AccountConfig` CTI schema additions        | Add `cti_match_fields`, `cti_provider_match_enabled`, and `cti_screenpop_trigger` plus Alembic migration.           |
| S11-03 | Flask Backend  |    L | Backlog | High     | ZCC CTI middleware endpoint                 | Add `POST /cti/screenpop` to receive caller context, perform ordered lookup, and return match plus deep-link URL.   |
| S11-04 | Flask Backend  |    L | Backlog | High     | FHIR patient lookup service                 | Implement lookup functions for phone, DOB, last4 SSN, and patient ID, composed by the configured match chain.       |
| S11-05 | Flask Backend  |    M | Backlog | Medium   | Provider match lookup                       | Resolve provider from ZCC context via `ProviderMapping.zoom_user_id` and return provider profile context.           |
| S11-06 | Flask Backend  |    S | Backlog | Medium   | OpenEMR deep-link URL builder               | Build direct chart URLs like `{OPENEMR_PUBLIC_URL}/interface/patient_file/summary/demographics.php?set_pid={pid}`.  |
| S11-07 | Research       |    M | Backlog | High     | ZCC Flow configuration                      | Document inbound call flow setup, caller ANI capture, `/cti/screenpop` trigger, and trigger timing.                 |
| S11-08 | Flask Backend  |    S | Backlog | Medium   | No-match screen pop                         | Return new patient URL when all match fields fail: `{OPENEMR_PUBLIC_URL}/interface/patient_file/patient_file.php`.  |
| S11-09 | React Frontend |    M | Backlog | Medium   | CTI configuration UI                        | Add match field ordering, enable/disable toggles, screen pop trigger, and provider match setting to account config. |
| S11-10 | QA             |    L | Backlog | High     | End-to-end CTI test                         | Simulate inbound ZCC call through Flow, middleware lookup, patient match/no-match, and Smart Embed screen pop.      |

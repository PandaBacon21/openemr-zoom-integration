# Epic-ZCC CTI Screen Pop — Handoff (Sprint 11 QA)

> **SUPERSEDED (2026-07).** This is a point-in-time debugging handoff kept for
> historical context. Current behavior has since changed: outbound RC3
> (`ContactType=Outgoing`) now pops a small "Calling…" confirmation modal —
> there is no outbound patient chart navigation, and the PatientLookUp cache
> preload (`matched_on=outbound_context`) was removed. Click-to-call is
> restricted to the patient Demographics contact section, and
> `dynamic_finder.php` was deleted (reverted to stock OpenEMR). The rest of
> this doc is left as-is for historical reference.

> Written: 2026-06-24 for context continuation. The immediate priority is diagnosing
> why `ReceiveCommunication3` phone lookup returns 0 matches even after the E.164 fix.

> Current status: this handoff is historical. The active implementation now uses
> a phone-keyed PatientLookUp cache for both inbound PatientLookUp handoff and
> outbound click-to-dial context preload. There is no separate
> `outbound_call_cache.py`; click-to-dial and manual dialing are expected to work
> through ZCC initiate-call plus ReceiveCommunication3 screen-pop routing.
> OpenEMR CTI controls are now session-gated to active ZCC-agent streams; non-ZCC
> users see plain phone numbers. Demo seed numbers ending in `555-####` are not
> made clickable.

---

## What is this?

Zoomly impersonates an Epic backend for Zoom Contact Center (ZCC) CTI integration.
The goal is: when a ZCC agent takes a call (inbound or outbound), OpenEMR automatically
navigates to the relevant patient record. This is driven by:

1. **`/cti/initiate-call`** — OpenEMR PHP calls Flask when an agent clicks a phone link
   in the browser (click-to-dial)
2. **`ReceiveCommunication3`** — ZCC calls Flask to notify Epic of call events
3. **SSE stream** (`/screenpop/stream`) — Flask pushes navigation events to the
   agent's OpenEMR browser session via `cti_subscriber.js`

---

## Historical Broken Behavior

The following issue was observed during the 2026-06-24 QA pass and is retained
for context only.

Josh ran three QA tests on 2026-06-24:

| Test | Expected | Actual |
|------|----------|--------|
| Click-to-dial from OpenEMR phone link | Patient record opens | Patient record opens ✓ then **patient finder opens** ✗ |
| Manual dial from ZCC CTI iframe | Patient record opens | **Patient finder opens** ✗ |
| Inbound call with DOB collected in ZCC IVR | Patient record opens | **Patient finder opens** ✗ |

The patient finder (`dynamic_finder.php`) opens when `ReceiveCommunication3` dispatches
an SSE event with only `caller_number` and no `openemr_patient_id`. This happens when
the phone/DOB/SSN lookup in `communication.py` returns 0 or multiple matches.

---

## Audit Log Evidence

From `AuditLog` table as of 2026-06-24 04:42 UTC (latest click-to-dial after code changes):

```
04:42:04 epic_zcc.click_to_dial_initiated
  {"agent_id": "Y9_oro4RQvioWPLY6Efahg", "zcc_status_code": 200,
   "phone_system_call_id": null, "has_patient_context": true}

04:42:07 epic_zcc.receive_communication_received
  {"recipient_id": "Y9_oro4RQvioWPLY6Efahg", "patient_id_type": null,
   "has_patient_id": false, "communication_type": "Phone", "call_id": "Jbkayp5uRkyREYnccAD5Hg"}

04:42:07 epic_zcc.receive_communication_pushed
  {"recipient_id": "Y9_oro4RQvioWPLY6Efahg", "subscriber_count": 1,
   "matched_on": "phone_no_match", "match_count": 0, "search_type": "phone",
   "call_id": "Jbkayp5uRkyREYnccAD5Hg"}
```

Key observations:
- `search_type: phone` confirms the new code is deployed and running
- `has_patient_id: false` — ZCC sends NO patient identifier (DOB/MRN/SSN) for click-to-dial
- `match_count: 0` — the phone lookup is finding zero patients

**The critical unknown: what phone number did ZCC send in `CallerPhoneNumber` /
`DialedPhoneNumber`?** The current audit does NOT log these values. This is the
first thing to diagnose.

Earlier tests (BEFORE code changes, old `no_outbound_call_record` reason):
```
04:29:17 receive_communication_received: patient_id_type: "SS" (SSN test — pre-fix)
04:04:34 receive_communication_received: patient_id_type: "DOB" (DOB test — pre-fix)
```

---

## Historical Changes From The 2026-06-24 Session

### Files modified:

**`server/app/blueprints/epic/outbound_routes.py`**
- Fixed missing `zoom_account_id: str` parameter on `cti_initiate_call()` (pre-existing Flask routing bug)
- Replaced the old outbound-call cache approach. Current code calls ZCC's Epic initiate-call API and, after ZCC accepts it, preloads the PatientLookUp cache with the known OpenEMR patient under the normalized dialed phone number.

**`server/app/services/epic/communication.py`**
- ReceiveCommunication3 can consume the phone-keyed PatientLookUp cache or fall back to direct lookup criteria from the ReceiveCommunication3 payload.
- `_build_rc3_criteria` maps `patient_id_type` → search criterion:
  - `DOB` → `search_patients({"dob": patient_id})`
  - `SS`/`SSN` → `search_patients({"ssn_last4": last4})`
  - `MRN`/`EPI`/`EPIID` → `search_patients({"patient_id": ..., "patient_id_type": "MRN"})`
  - `FHIR`/`FHIRID` → `search_patients({"patient_id": ..., "patient_id_type": "FHIR"})`
  - Fallback: phone from `DialedPhoneNumber` (outgoing) or `CallerPhoneNumber` (incoming)
- No-match / ambiguous dispatches SSE with `caller_number` only → JS navigates to `dynamic_finder.php?search_any={phone}`
- Audit `matched_on` now encodes both the lookup type and result: `dob_no_match`, `phone_ambiguous`, etc.

**`server/app/services/epic/request_parser.py`**
- Added `contact_type` field to both JSON and XML parsers (was not extracted from `ContactType`)

**`server/app/services/epic/patient_search.py`**
- `_phone_digits()` now strips leading `1` country code from 11-digit US E.164 numbers:
  `+13035550101` → `13035550101` → `3035550101` (10-digit, matches OpenEMR stored format)

**`server/app/services/epic/lookup_cache.py`**
- Holds short-lived PatientLookUp results by `(zoom_account_id, phone_digits)`.
- Outbound click-to-dial preloads this same cache with `matched_on=outbound_context`; there is no separate outbound-call cache.

**Tests updated:**
- `server/tests/test_blueprint_epic_communication.py` — replaced cache-based tests with phone/DOB path tests
- `server/tests/test_blueprint_epic_outbound.py` — replaced cache assertion with SSE queue check

All 15 affected tests pass.

---

## Root Cause Hypothesis for Remaining Bug

The phone lookup returns 0 results for the click-to-dial ReceiveCommunication3. There are
three likely causes to investigate in order:

### 1. ZCC sends no phone (most likely for click-to-dial)
`receive_communication_received` shows `has_patient_id: false` — no `LookupID` or
`LookupInformation`. The code then falls to phone lookup. But if ZCC also sends no
`DialedPhoneNumber` and no `CallerPhoneNumber` in the click-to-dial ReceiveCommunication3,
both would be `None`, `criteria = {}` → `no_lookup_criteria` failure. But the audit shows
`search_type: phone`, meaning at least one phone field was present. However, it might be
the AGENT's phone (their own extension/caller ID) rather than the patient's phone.

**Diagnostic step:** Log `caller_number` and `dialed_number` in `communication_routes.py`'s
`receive_communication_received` audit detail. They are already extracted by the parser and
available in `payload` — just need to add them to the audit call at line 82.

### 2. E.164 fix not catching all formats
The `_phone_digits` fix handles `+1XXXXXXXXXX` (11 digits starting with 1). If ZCC sends
a different format (e.g., `001XXXXXXXXXX`, `(XXX) XXX-XXXX`, or a number without country
code already), the normalization may not match OpenEMR's stored 10-digit format.

### 3. OpenEMR phone format in seed data
Check what format phone numbers are stored in `patient_data.phone_cell` / `phone_home`
for the test patient. Run:
```sql
SELECT pid, fname, lname, phone_cell, phone_home
FROM patient_data
WHERE pid = {test_patient_pid};
```

---

## First Debugging Steps

1. **Add `caller_number` and `dialed_number` to the `receive_communication_received` audit.**
   In `server/app/blueprints/epic/communication_routes.py` around line 77:
   ```python
   write_audit_log(
       event_type="epic_zcc.receive_communication_received",
       ...
       detail={
           "recipient_id": payload["recipient_id"],
           "patient_id_type": payload.get("patient_id_type"),
           "has_patient_id": bool(payload.get("patient_id")),
           "communication_type": payload.get("communication_type"),
           "contact_type": payload.get("contact_type"),      # ADD
           "caller_number": payload.get("caller_number"),    # ADD
           "dialed_number": payload.get("dialed_number"),    # ADD
           "call_id": payload.get("call_id"),
       },
   )
   ```
   Re-run click-to-dial and check audit to see what ZCC actually sent.

2. **Check whether ZCC sends any phone for click-to-dial at all.** The `phone_system_call_id: null`
   in `click_to_dial_initiated` suggests ZCC's initiate-call response doesn't return a
   call ID either, which may indicate ZCC's behavior for this flow is minimal.

3. **If ZCC sends the wrong phone (agent's number instead of patient's):** The current
   click-to-dial path preloads the phone-keyed PatientLookUp cache with the known
   patient under the dialed number. If ZCC later echoes a different phone in
   ReceiveCommunication3, the correlation strategy would need to change.

---

## Architecture Overview

```
OpenEMR browser (cti_subscriber.js)
  └─ SSE GET /screenpop/stream
       └─ screenpop_dispatch.py (Queue per openemr_user_id)
            ↑ dispatch() called from:
              • outbound_routes.py  (click-to-dial — cache preload after ZCC accepts initiate-call)
              • communication.py    (ReceiveCommunication3 — from ZCC)

ZCC CTI integration calls:
  GET  /oauth2/token                                        (bearer token)
  POST /api/epic/.../PatientLookUp/.../PatientLookUp2012   (inbound IVR lookup)
  POST /api/epic/.../RECEIVECOMMUNICATION3/ReceiveCommunication3
  POST /cti/initiate-call                                   (HMAC signed, from PHP)
```

---

## Relevant Files

| File | Purpose |
|------|---------|
| `server/app/blueprints/epic/communication_routes.py` | ReceiveCommunication3 route — **add phone logging here** |
| `server/app/services/epic/communication.py` | `process_receive_communication()` + `_build_rc3_criteria()` |
| `server/app/services/epic/patient_search.py` | `search_patients()` + `_phone_digits()` |
| `server/app/services/epic/screenpop_dispatch.py` | SSE queue dispatch |
| `server/app/blueprints/epic/outbound_routes.py` | `cti_initiate_call()` — calls ZCC initiate-call and preloads PatientLookUp cache |
| `server/app/services/epic/lookup_cache.py` | Short-lived phone-keyed PatientLookUp cache, also used by outbound click-to-dial context preload |
| `openemr/patches/epic_cti/initiate_call.php` | PHP bridge for click-to-dial |
| `openemr/patches/epic_cti/cti_subscriber.js` | Browser SSE consumer + `buildNavigation()` |
| `openemr/patches/epic_cti/cti_phone_inject.js` | Shared phone-link click-to-call helper; skips demo seed `555-####` numbers |

---

## Known ZCC Issues (open, pending Zoom response)

From CLAUDE.md `Zoom ZCC — Open Engineering Items`:

- **PatientLookUp / ReceiveCommunication3 sequencing** — confirm the exact ZCC Flow
  configuration that drives PatientLookUp before ReceiveCommunication3 for inbound
  calls. ReceiveCommunication3 can also search from direct criteria, but the intended
  high-confidence path is PatientLookUp cache -> ReceiveCommunication3.

- **Screen-pop cache scaling** — the PatientLookUp cache is process-local and
  consistent with the current one-worker Gunicorn deployment. Multi-worker or
  multi-replica deployments need a shared cache or different correlation strategy.

---

## Sprint 11 QA Checklist Status

- [x] S11-QA01 — Click-to-dial confirmation across CTI surfaces (c5cd79e)
- [x] S11-QA03 — Close calendar modal on screen pop
- [x] S11-QA04 — Auto-expand CTI panel on call
- [x] **S11-QA (current)** — Screen pop navigates to correct patient for click-to-dial and manual dialing
- [ ] Issue 2 — ZCC auth persists across OpenEMR user logins — not started
- [x] S11-10 — React `EpicZccTab` for SE configuration
- [x] S11-11 — `epic_zcc` feature flag end-to-end
- [ ] S11-12 — End-to-end QA — blocked on screen pop

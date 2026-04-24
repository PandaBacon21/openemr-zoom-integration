import logging
import requests
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from flask import current_app
from app.auth.jwt_assertion import get_openemr_token
from app.models import ZoomAccount
from app.extensions import get_openemr_db_engine

logger = logging.getLogger(__name__)


def get_practitioners(
    zoom_account: ZoomAccount,
    search: str | None = None,
    practitioner_id: str | None = None
) -> list[dict]:
    """
    Fetch Practitioner resources from OpenEMR FHIR API.

    Args:
        zoom_account: The ZoomAccount to use for authentication
        search: Optional name search string
        practitioner_id: Optional FHIR Practitioner UUID to fetch a single provider

    Returns: List of simplified provider dicts
    """
    fhir_base = current_app.config["OPENEMR_FHIR_BASE_URL"]
    token = get_openemr_token(zoom_account)

    if practitioner_id:
        url = f"{fhir_base}/Practitioner/{practitioner_id}"
    else:
        url = f"{fhir_base}/Practitioner"

    params = {}
    if search:
        params["name"] = search

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=10
    )
    response.raise_for_status()
    data = response.json()

    if practitioner_id:
        return [_normalize_practitioner(data)]

    # Bundle response — deduplicate by id
    entries = data.get("entry", [])
    seen = set()
    practitioners = []
    for entry in entries:
        resource = entry.get("resource", {})
        fhir_id = resource.get("id")
        if fhir_id and fhir_id not in seen:
            seen.add(fhir_id)
            practitioners.append(_normalize_practitioner(resource))

    return practitioners


def get_patient(
    zoom_account: ZoomAccount,
    pid: int | str,
) -> dict | None:
    """
    Fetch a Patient resource from OpenEMR FHIR API by OpenEMR patient ID (pid).
 
    OpenEMR exposes pid as the identifier value on the Patient resource
    using the http://terminology.hl7.org/CodeSystem/v2-0203 system.
    We query with ?identifier={pid} to resolve it to the FHIR resource.
 
    Args:
        zoom_account: The ZoomAccount to use for authentication
        pid: OpenEMR patient ID integer (from appointment payload)
 
    Returns:
        Normalized patient dict, or None if not found.
    """
    fhir_base = current_app.config["OPENEMR_FHIR_BASE_URL"]
    token = get_openemr_token(zoom_account)
 
    response = requests.get(
        f"{fhir_base}/Patient",
        headers={"Authorization": f"Bearer {token}"},
        params={"identifier": str(pid)},
        timeout=10
    )
    response.raise_for_status()
    data = response.json()
 
    entries = data.get("entry", [])
    if not entries:
        logger.warning(f"openemr.get_patient | No FHIR Patient found for pid={pid}")
        return None
 
    # Take the first match — pid is unique so there should only be one
    resource = entries[0].get("resource", {})
    return _normalize_patient(resource)


def _normalize_patient(resource: dict) -> dict:
    """
    Normalize a FHIR Patient resource into a clean dict.
    Extracts name, contact details, and identifiers needed
    for meeting topic building and future communications.
    """
    name = resource.get("name", [{}])[0]
    given = name.get("given", [])
    family = name.get("family", "")
    prefix = name.get("prefix", [])
 
    # Extract pid from identifier array
    pid = None
    for identifier in resource.get("identifier", []):
        if identifier.get("type", {}).get("coding", [{}])[0].get("code") == "PT":
            pid = identifier.get("value")
            break
 
    # Extract phone and email from telecom array
    phone = None
    email = None
    for telecom in resource.get("telecom", []):
        system = telecom.get("system")
        if system == "phone" and phone is None:
            phone = telecom.get("value")
        elif system == "email" and email is None:
            email = telecom.get("value")
 
    return {
        "fhir_id": resource.get("id"),
        "pid": pid,
        "active": resource.get("active", False),
        "first_name": " ".join(given),
        "last_name": family,
        "full_name": f"{' '.join(prefix)} {' '.join(given)} {family}".strip(),
        "gender": resource.get("gender"),
        "birth_date": resource.get("birthDate"),
        "phone": phone,
        "email": email,
    }


def _normalize_practitioner(resource: dict) -> dict:
    """
    Normalize a FHIR Practitioner resource into a clean dict
    for our API response.
    """
    name = resource.get("name", [{}])[0]
    given = name.get("given", [])
    family = name.get("family", "")
    prefix = name.get("prefix", [])

    npi = None
    for identifier in resource.get("identifier", []):
        if "us-npi" in identifier.get("system", ""):
            npi = identifier.get("value")
            break

    email = None
    for telecom in resource.get("telecom", []):
        if telecom.get("system") == "email":
            email = telecom.get("value")
            break

    # Look up users.id from OpenEMR DB using NPI.
    # This is the integer used as pc_aid / form_provider in appointment events
    # and needs to be stored on ProviderMapping for the webhook hot path.
    users_id = None
    if npi:
        try:
            engine = get_openemr_db_engine()
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT id FROM users WHERE npi = :npi LIMIT 1"),
                    {"npi": npi}
                ).fetchone()
                if row:
                    users_id = row.id
        except Exception as e:
            logger.warning(f"_normalize_practitioner | Failed to look up users.id for npi={npi}: {e}")

    return {
        "fhir_id": resource.get("id"),
        "active": resource.get("active", False),
        "first_name": " ".join(given),
        "last_name": family,
        "full_name": f"{' '.join(prefix)} {' '.join(given)} {family}".strip(),
        "npi": npi,
        "email": email,
        "users_id": users_id,
    }


def get_appointment_types_list() -> list[dict]:
    """
    Query OpenEMR appointment categories directly from MariaDB.
    No API endpoint exists for this resource in OpenEMR 8.0.0.
    """
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT pc_catid, pc_catname, pc_catdesc, pc_duration, pc_catcolor
            FROM openemr_postcalendar_categories
            WHERE pc_active = 1
            ORDER BY pc_seq
        """))
        return [
            {
                "id": str(row.pc_catid),
                "name": row.pc_catname,
                "description": row.pc_catdesc,
                "duration_seconds": row.pc_duration,
                "color": row.pc_catcolor,
            }
            for row in result
        ]


def write_zoom_urls_to_appointment(
    eid: int,
    start_url: str,
    join_url: str
) -> bool:
    """
    Write Zoom meeting URLs back to the OpenEMR appointment record.

    Uses direct MariaDB connection — the FHIR Appointment resource
    is read-only in OpenEMR 8.0, so there is no API path for this write.

    Fields updated:
      pc_hometext — provider/staff facing notes field
                    Written as "Zoom Meeting: {start_url}"
      pc_website  — URL field on the appointment, used for patient join URL

    Args:
        eid:       OpenEMR appointment ID (pc_eid)
        start_url: Zoom host start URL (provider/alternative host)
        join_url:  Zoom patient join URL

    Returns:
        True if the update affected a row, False if eid not found.
    """
    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE openemr_postcalendar_events
                    SET
                        pc_website = :website
                    WHERE pc_eid = :eid
                """),
                {
                    "website": start_url,
                    "eid": int(eid),
                }
            )

        if result.rowcount == 0:
            logger.warning(
                f"openemr.write_zoom_urls | No appointment found for eid={eid}"
            )
            return False

        logger.info(
            f"openemr.write_zoom_urls | Written Zoom URLs to appointment eid={eid}"
        )
        return True

    except Exception as e:
        logger.error(
            f"openemr.write_zoom_urls | Failed to write URLs for eid={eid}: {e}"
        )
        return False


# Update Appointment Status - should automatically create Encounter if not already done
def update_appointment_status(eid: int, status: str = "@") -> bool:
    """
    Update appointment status on openemr_postcalendar_events.
    
    Status codes:
      '@' = Arrived (triggers auto-create encounter)
      '-' = None
      '*' = Reminder done
      '+' = Chart pulled
      'x' = Canceled
      '?' = No show
    
    Args:
        eid:    OpenEMR appointment ID (pc_eid)
        status: Single character status code, default '@' (Arrived)
    
    Returns:
        True if row was updated, False if eid not found
    """

    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE openemr_postcalendar_events
                    SET pc_apptstatus = :status
                    WHERE pc_eid = :eid
                """),
                {"status": status, "eid": int(eid)}
            )
        if result.rowcount == 0:
            logger.warning(f"openemr.update_appointment_status | No appointment found for eid={eid}")
            return False
        logger.info(f"openemr.update_appointment_status | eid={eid} status updated to '{status}'")
        return True
    except Exception as e:
        logger.error(f"openemr.update_appointment_status | Failed for eid={eid}: {e}")
        return False


def create_encounter(
    pid: int,
    provider_id: int,
    facility_id: int,
    pc_catid: int,
    eid: int,
    reason: str = "Zoom Telehealth Visit",
    class_code: str = "VR",
) -> int | None:
    """
    Create a new encounter in OpenEMR linked to a Zoom appointment.

    Replicates what OpenEMR's auto-create encounter does when appointment
    status is changed to Arrived via the UI.
    - changing via the direct DB connection does not trigger the auto-create function
    

    Uses the sequences table to get the next encounter number atomically.
    Sets external_id = 'zoom_eid_{eid}' for reliable lookup later.

    Args:
        pid:         OpenEMR patient ID
        provider_id: OpenEMR provider users.id
        facility_id: OpenEMR facility ID
        pc_catid:    Calendar category ID (appointment type)
        eid:         OpenEMR appointment EID (stored in external_id)
        reason:      Reason for visit text
        class_code:  HL7 encounter class — 'VR' for virtual

    Returns:
        encounter number (int) if successful, None on failure
    """

    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            # Check if encounter already exists for this eid
            existing = conn.execute(
                text("SELECT encounter FROM form_encounter WHERE external_id = :external_id"),
                {"external_id": f"zoom_eid_{eid}"}
            ).fetchone()

            if existing:
                logger.info(f"openemr.create_encounter | Encounter already exists for eid={eid}, skipping")
                return existing.encounter
            
            # --- 1. If not existing - Get next encounter number atomically ---
            conn.execute(text("UPDATE sequences SET id = id + 1"))
            result = conn.execute(text("SELECT id FROM sequences"))
            encounter_number = result.scalar()

            # --- 2. Insert form_encounter ---
            encounter_uuid = uuid.uuid4().bytes
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")

            conn.execute(
                text("""
                    INSERT INTO form_encounter (
                        uuid, date, pid, encounter,
                        pc_catid, provider_id, facility_id,
                        billing_facility, class_code,
                        reason, external_id,
                        sensitivity, in_collection
                    ) VALUES (
                        :uuid, :date, :pid, :encounter,
                        :pc_catid, :provider_id, :facility_id,
                        :billing_facility, :class_code,
                        :reason, :external_id,
                        '', 0
                    )
                """),
                {
                    "uuid": encounter_uuid,
                    "date": today,
                    "pid": int(pid),
                    "encounter": encounter_number,
                    "pc_catid": int(pc_catid),
                    "provider_id": int(provider_id),
                    "facility_id": int(facility_id),
                    "billing_facility": int(facility_id),
                    "class_code": class_code,
                    "reason": reason,
                    "external_id": f"zoom_eid_{eid}",
                }
            )
            # Look up provider username for forms.user field
            user_result = conn.execute(
                text("SELECT username FROM users WHERE id = :provider_id"),
                {"provider_id": int(provider_id)}
            )
            row = user_result.fetchone()
            provider_username = row.username if row else "admin"

            # --- 3. Insert forms table entry to link encounter form ---
            forms_result = conn.execute(
                text("""
                    INSERT INTO forms (
                        date, encounter, form_name, formdir,
                        pid, authorized, deleted, provider_id, user, groupname
                    ) VALUES (
                        :date, :encounter, :form_name, :formdir,
                        :pid, 1, 0, :provider_id, :user, 'Default'
                    )
                """),
                {
                    "date": now,
                    "encounter": encounter_number,
                    "form_name": "New Patient Encounter",
                    "formdir": "newpatient",
                    "pid": int(pid),
                    "provider_id": int(provider_id),
                    "user": provider_username
                }
            )
            # --- 4. Set form_id to self-referential id ---
            forms_id = forms_result.lastrowid
            conn.execute(
                text("UPDATE forms SET form_id = :form_id WHERE id = :id"),
                {"form_id": forms_id, "id": forms_id}
            )

        logger.info(
            f"openemr.create_encounter | Created encounter={encounter_number} "
            f"pid={pid} eid={eid} provider={provider_id}"
        )
        return encounter_number

    except Exception as e:
        logger.error(f"openemr.create_encounter | Failed for pid={pid} eid={eid}: {e}")
        return None


def get_appointment_details(eid: int) -> dict | None:
    """Get appointment fields needed for encounter creation."""

    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    SELECT pc_pid, pc_aid, pc_facility, pc_catid
                    FROM openemr_postcalendar_events
                    WHERE pc_eid = :eid
                """),
                {"eid": int(eid)}
            )
            row = result.fetchone()
            if not row:
                return None
            return {
                "pid": row.pc_pid,
                "provider_id": row.pc_aid,
                "facility_id": row.pc_facility,
                "pc_catid": row.pc_catid,
            }
    except Exception as e:
        logger.error(f"openemr.get_appointment_details | Failed for eid={eid}: {e}")
        return None
    


"""
MOVE DURING REFACTOR
"""

# ---------------------------------------------------------------------------
# SOAP section mapping
# ---------------------------------------------------------------------------
 
# Maps Zoom note section headers to SOAP fields.
# Keys are lowercase for case-insensitive matching.
SOAP_SECTION_MAP = {
    # Subjective
    "chief complaint":                  "subjective",
    "history of present illness":       "subjective",
    "hpi":                              "subjective",
    "review of systems":                "subjective",
    "ros":                              "subjective",
    "symptoms and stressors":           "subjective",
    "subjective narrative":             "subjective",
    "discussion notes":                 "subjective",
    "reason for visit":                 "subjective",
    "past medical history":             "subjective",
    "past psychiatric history":         "subjective",
    "past surgical history":            "subjective",
    "family history":                   "subjective",
    "social history":                   "subjective",
    "medications":                      "subjective",
    "allergies":                        "subjective",
    "immunizations":                    "subjective",
    "development history":              "subjective",
    "anticipatory guidance":            "subjective",
    "diet & nutrition":                 "subjective",
    "diet and nutrition":               "subjective",
 
    # Objective
    "physical exam":                    "objective",
    "vitals":                           "objective",
    "results":                          "objective",
    "mental status exam":               "objective",
    "functional status":                "objective",
    "procedures":                       "objective",
    "hospital / ed course":             "objective",
    "hospital course":                  "objective",
    "ed course":                        "objective",
    "response to therapy":              "objective",
 
    # Assessment
    "assessment":                       "assessment",
    "risk assessment":                  "assessment",
    "problem list":                     "assessment",
    "generated diagnoses & codes":      "assessment",
    "generated diagnoses and codes":    "assessment",
 
    # Plan
    "plan":                             "plan",
    "assessment & plan":                "plan",
    "assessment and plan":              "plan",
    "patient recommendations":          "plan",
    "goals narrative":                  "plan",
    "disposition":                      "plan",
    "advanced directives":              "plan",
}
 

def parse_soap_sections(note_content: str) -> dict:
    """
    Parse Zoom clinical note content into SOAP sections.
 
    The note_content is plain text with section headers followed by content.
    Section headers are lines that match known Zoom section names.
    Content continues until the next section header.
 
    Unrecognized sections default to 'subjective' as a catch-all.
 
    Args:
        note_content: Raw note_content string from Zoom clinical notes API
 
    Returns:
        dict with keys: subjective, objective, assessment, plan
        Each value is a string of accumulated content for that section.
    """
    sections = {"subjective": [], "objective": [], "assessment": [], "plan": []}
    current_field = "subjective"  # default catch-all
    current_header = None
    buffer = []
 
    def flush_buffer():
        if buffer and current_header is not None:
            content = "\n".join(buffer).strip()
            if content:
                sections[current_field].append(f"{current_header}\n{content}")
        buffer.clear()
 
    for line in note_content.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
 
        # Check if this line is a known section header
        matched_field = SOAP_SECTION_MAP.get(lower)
 
        if matched_field is not None:
            # Flush previous section buffer
            flush_buffer()
            current_field = matched_field
            current_header = stripped
        else:
            buffer.append(stripped)
 
    # Flush final buffer
    flush_buffer()
 
    return {
        "subjective":  "\n\n".join(sections["subjective"]),
        "objective":   "\n\n".join(sections["objective"]),
        "assessment":  "\n\n".join(sections["assessment"]),
        "plan":        "\n\n".join(sections["plan"]),
    }
 
 
def find_encounter_for_appointment(eid: int, pid: int, provider_id: int) -> int | None:
    """
    Find an existing encounter for a given appointment.

    Lookup order:
        1. external_id = 'zoom_eid_{eid}'  (created by waiting room webhook)
        2. Most recent encounter for pid + provider_id on today's date
            (created manually via UI status change)

    Args:
        eid:         OpenEMR appointment EID
        pid:         OpenEMR patient ID
        provider_id: OpenEMR provider users.id

    Returns:
        encounter number (int) or None if not found
    """
    from sqlalchemy import text
    from app.extensions import get_openemr_db_engine
    from datetime import datetime, timezone

    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            # --- 1. Check by external_id ---
            result = conn.execute(
                text("""
                    SELECT encounter FROM form_encounter
                    WHERE external_id = :external_id
                    LIMIT 1
                """),
                {"external_id": f"zoom_eid_{eid}"}
            ).fetchone()

            if result:
                logger.info(
                    f"openemr.find_encounter | Found by external_id zoom_eid_{eid} "
                    f"→ encounter={result.encounter}"
                )
                return result.encounter

            # --- 2. Fall back to most recent encounter for pid + provider + today ---
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            result = conn.execute(
                text("""
                    SELECT encounter FROM form_encounter
                    WHERE pid = :pid
                    AND provider_id = :provider_id
                    AND DATE(date) = :today
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {
                    "pid": int(pid),
                    "provider_id": int(provider_id),
                    "today": today,
                }
            ).fetchone()

            if result:
                logger.info(
                    f"openemr.find_encounter | Found by pid+provider+date "
                    f"pid={pid} provider={provider_id} → encounter={result.encounter}"
                )
                return result.encounter

    except Exception as e:
        logger.error(f"openemr.find_encounter | Failed for eid={eid}: {e}")

    return None


def write_note_to_encounter(
    encounter_number: int,
    pid: int,
    provider_id: int,
    provider_username: str,
    note_content: str,
    note_title: str,
    note_id: str,
) -> bool:
    """
    S5-05: Write Zoom clinical note into an OpenEMR encounter.
 
    Writes to two forms:
      1. form_soap      — parsed SOAP sections (subjective/objective/assessment/plan)
      2. form_clinical_notes — full note content as a clinical note narrative
 
    Both forms are registered in the forms table linked to the encounter.
 
    Args:
        encounter_number:  OpenEMR encounter number
        pid:               OpenEMR patient ID
        provider_id:       OpenEMR provider users.id
        provider_username: OpenEMR provider username (for forms.user field)
        note_content:      Raw note_content from Zoom clinical notes API
        note_title:        Note title from Zoom webhook payload
        note_id:           Zoom note ID (stored in external_id for dedup)
 
    Returns:
        True if successful, False on error
    """
    from sqlalchemy import text
    from app.extensions import get_openemr_db_engine
    import uuid
    from datetime import datetime, timezone
 
    engine = get_openemr_db_engine()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
 
    # Parse note content into SOAP sections
    soap = parse_soap_sections(note_content)
 
    try:
        with engine.begin() as conn:
 
            # ----------------------------------------------------------------
            # 1. Write SOAP note
            # ----------------------------------------------------------------
            soap_result = conn.execute(
                text("""
                    INSERT INTO form_soap (
                        date, pid, user, groupname,
                        authorized, activity,
                        subjective, objective, assessment, plan
                    ) VALUES (
                        :date, :pid, :user, 'Default',
                        1, 1,
                        :subjective, :objective, :assessment, :plan
                    )
                """),
                {
                    "date": now,
                    "pid": int(pid),
                    "user": provider_username,
                    "subjective": soap["subjective"],
                    "objective":  soap["objective"],
                    "assessment": soap["assessment"],
                    "plan":       soap["plan"],
                }
            )
            soap_form_id = soap_result.lastrowid
 
            # Register SOAP form in forms table
            soap_forms_result = conn.execute(
                text("""
                    INSERT INTO forms (
                        date, encounter, form_name, formdir,
                        pid, user, groupname, authorized,
                        deleted, form_id, provider_id
                    ) VALUES (
                        :date, :encounter, 'SOAP', 'soap',
                        :pid, :user, 'Default', 1,
                        0, :form_id, :provider_id
                    )
                """),
                {
                    "date":        now,
                    "encounter":   encounter_number,
                    "pid":         int(pid),
                    "user":        provider_username,
                    "form_id":     soap_form_id,
                    "provider_id": int(provider_id),
                }
            )
 
            # ----------------------------------------------------------------
            # 2. Write Clinical Notes form (full narrative)
            # ----------------------------------------------------------------
            cn_uuid = uuid.uuid4().bytes
            cn_result = conn.execute(
                text("""
                    INSERT INTO form_clinical_notes (
                        form_id, uuid, date, pid, encounter,
                        user, groupname, authorized, activity,
                        code, codetext, description, external_id,
                        clinical_notes_type, clinical_notes_category
                    ) VALUES (
                        0, :uuid, :date, :pid, :encounter,
                        :user, 'Default', 1, 1,
                        'zoom-clinical-note', :codetext, :description, :external_id,
                        'Evaluation Note', 'General'
                    )
                """),
                {
                    "uuid":        cn_uuid,
                    "date":        today,
                    "pid":         int(pid),
                    "encounter":   str(encounter_number),
                    "user":        provider_username,
                    "codetext":    note_title,
                    "description": note_content,
                    "external_id": note_id,
                }
            )
            cn_id = cn_result.lastrowid
 
            # Update form_clinical_notes.form_id to self-referential id
            conn.execute(
                text("UPDATE form_clinical_notes SET form_id = :id WHERE id = :id"),
                {"id": cn_id}
            )
 
            # Register Clinical Notes form in forms table
            conn.execute(
                text("""
                    INSERT INTO forms (
                        date, encounter, form_name, formdir,
                        pid, user, groupname, authorized,
                        deleted, form_id, provider_id
                    ) VALUES (
                        :date, :encounter, 'Clinical Notes', 'clinical_notes',
                        :pid, :user, 'Default', 1,
                        0, :form_id, :provider_id
                    )
                """),
                {
                    "date":        now,
                    "encounter":   encounter_number,
                    "pid":         int(pid),
                    "user":        provider_username,
                    "form_id":     cn_id,
                    "provider_id": int(provider_id),
                }
            )
 
        logger.info(
            f"openemr.write_note_to_encounter | Written SOAP + Clinical Notes "
            f"to encounter={encounter_number} pid={pid} note_id={note_id}"
        )
        return True
 
    except Exception as e:
        logger.error(
            f"openemr.write_note_to_encounter | Failed for "
            f"encounter={encounter_number} pid={pid}: {e}"
        )
        return False
 

def get_provider_username(provider_id: int) -> str | None:
    from sqlalchemy import text
    from app.extensions import get_openemr_db_engine
    
    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT username FROM users WHERE id = :id"),
                {"id": int(provider_id)}
            ).fetchone()
            return result.username if result else None
    except Exception as e:
        logger.error(f"openemr.get_provider_username | Failed: {e}")
        return None
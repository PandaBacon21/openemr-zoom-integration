import logging
import requests
from flask import current_app
from app.auth.jwt_assertion import get_openemr_token
from app.models import ZoomAccount

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
            from sqlalchemy import text
            from app.extensions import get_openemr_db_engine
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


def get_appointment_types() -> list[dict]:
    """
    Query OpenEMR appointment categories directly from MariaDB.
    No API endpoint exists for this resource in OpenEMR 8.0.0.
    """
    from sqlalchemy import text
    from app.extensions import get_openemr_db_engine

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
    from sqlalchemy import text
    from app.extensions import get_openemr_db_engine

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

import logging
from datetime import date, time, timedelta

import requests
from sqlalchemy import text
from flask import current_app
from app.auth.jwt_assertion import get_openemr_token
from app.models import ZoomAccount, ProviderMapping
from app.extensions import db, get_openemr_db_engine

logger = logging.getLogger(__name__)


# Mapping from OpenEMR users.specialty (the canonical specialty string stored
# on the provider's user row) to the Zoom appointment category names this
# provider can offer in the Sprint 13 hydration flow. Unmapped specialties
# resolve to [] so the orchestrator can skip them explicitly rather than
# silently producing wrong-specialty appointments.
SPECIALTY_TO_CATEGORIES = {
    "Internal Medicine":              ["Zoom Chronic Care", "Zoom New Patient", "Zoom Preventive", "Zoom Established Patient"],
    "Family Medicine":                ["Zoom Chronic Care", "Zoom New Patient", "Zoom Preventive", "Zoom Established Patient"],
    "Psychiatry":                     ["Zoom Behavioral Health", "Zoom New Patient", "Zoom Established Patient"],
    "Psychiatric Nurse Practitioner": ["Zoom Behavioral Health", "Zoom New Patient", "Zoom Established Patient"],
    "Clinical Social Work":           ["Zoom Behavioral Health", "Zoom New Patient", "Zoom Established Patient"],
    "Addiction Medicine":             ["Zoom MAT (Suboxone)", "Zoom New Patient", "Zoom Established Patient"],
}


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


def get_provider_username(provider_id: int) -> str | None:

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


def get_provider_patients(provider_user_id: int) -> list[dict]:
    """
    Fetch all patients assigned to the given OpenEMR provider via patient_data.providerID.

    Excludes patients tagged as the dedicated demo past-encounter target
    (patient_data.referrer = 'Zoomly Demo Past Encounter') so future-appointment
    hydration still cycles through the Sprint 12 chronic-care / persona patients
    rather than scheduling every future visit on the diabetes demo patient.
    """
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT pid, fname, lname, DOB, sex "
                "FROM patient_data "
                "WHERE providerID = :provider_id "
                "  AND (referrer IS NULL OR referrer != 'Zoomly Demo Past Encounter') "
                "ORDER BY pid"
            ),
            {"provider_id": int(provider_user_id)}
        ).fetchall()
    return [
        {
            "pid": row.pid,
            "fname": row.fname,
            "lname": row.lname,
            "dob": row.DOB.isoformat() if row.DOB else None,
            "sex": row.sex,
        }
        for row in rows
    ]


def get_provider_specialty_categories(provider_user_id: int) -> list[str]:
    """
    Resolve the Zoom appointment categories appropriate for the provider's
    OpenEMR specialty (from users.specialty). Returns [] for unmapped or
    missing specialties so callers can decide what to do (skip hydration,
    fall back to a default, etc.) rather than silently producing
    wrong-specialty appointments.
    """
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT specialty FROM users WHERE id = :id"),
            {"id": int(provider_user_id)}
        ).fetchone()
    if not row or not row.specialty:
        return []
    # Return a fresh copy so callers can mutate (pop/rotate for round-robin)
    # without affecting the module-level constant or other callers.
    return list(SPECIALTY_TO_CATEGORIES.get(row.specialty, []))


def get_provider_appointments_in_window(
    provider_user_id: int,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Return all appointments for a provider within an inclusive date window.
    Used by the Sprint 13 hydration flow to evaluate which of the upcoming
    weekday slots already have appointments + Zoom meetings.

    pc_startTime is normalized from PyMySQL's timedelta back to a datetime.time
    so callers can compare against slot times directly without redoing the
    conversion at every callsite (per CLAUDE.md note on the MariaDB / PyMySQL
    TIME column quirk).
    """
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT pc_eid, pc_pid, pc_aid, pc_eventDate, pc_startTime,
                       pc_duration, pc_catid, pc_apptstatus, pc_website,
                       pc_title, pc_hometext
                FROM openemr_postcalendar_events
                WHERE pc_aid = :provider_id
                  AND pc_eventDate BETWEEN :start_date AND :end_date
                ORDER BY pc_eventDate, pc_startTime
            """),
            {
                "provider_id": int(provider_user_id),
                "start_date": start_date,
                "end_date": end_date,
            }
        ).fetchall()
    return [
        {
            "pc_eid": row.pc_eid,
            "pc_pid": row.pc_pid,
            "pc_aid": row.pc_aid,
            "pc_eventDate": row.pc_eventDate,
            "pc_startTime": _timedelta_to_time(row.pc_startTime),
            "pc_duration": row.pc_duration,
            "pc_catid": row.pc_catid,
            "pc_apptstatus": row.pc_apptstatus,
            "pc_website": row.pc_website,
            "pc_title": row.pc_title,
            "pc_hometext": row.pc_hometext,
        }
        for row in rows
    ]


def _timedelta_to_time(td: timedelta | None) -> time | None:
    if td is None:
        return None
    total = int(td.total_seconds())
    return time(total // 3600, (total % 3600) // 60, total % 60)


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

    # Look up users.id, facility_id, and facility name from OpenEMR DB by NPI.
    # users.id is the integer used as pc_aid / form_provider in appointment
    # events and needs to be stored on ProviderMapping for the webhook hot
    # path. facility_id + facility_name are captured at mapping creation time
    # for surface in the provider mappings table (S7-14) and future filtering.
    user_id = None
    facility_id = None
    facility_name = None
    if npi:
        try:
            engine = get_openemr_db_engine()
            with engine.connect() as conn:
                # JOIN against the `facility` table for the canonical facility
                # name — OpenEMR's `users.facility` (denormalized varchar) is
                # not reliably populated, so trust `facility.name` resolved
                # through `users.facility_id`. users.facility_id defaults to 0
                # when unset; LEFT JOIN keeps the row but yields NULL facility.
                row = conn.execute(
                    text("""
                        SELECT u.id, u.facility_id, f.name AS facility_name
                        FROM users u
                        LEFT JOIN facility f ON f.id = u.facility_id
                        WHERE u.npi = :npi
                        LIMIT 1
                    """),
                    {"npi": npi}
                ).fetchone()
                if row:
                    user_id = row.id
                    facility_id = row.facility_id or None
                    facility_name = row.facility_name or None
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
        "user_id": user_id,
        "facility_id": facility_id,
        "facility_name": facility_name,
    }


def _create_provider_mapping(
    zoom_account_id: str,
    openemr_fhir_id: str,
    openemr_provider_npi: str,
    openemr_provider_id: int | None,
    openemr_provider_name: str | None,
    zoom_user_id: str,
    zoom_user_email: str,
    zoom_user_name: str | None,
    zoom_user_type: int | None,
    openemr_facility_id: int | None = None,
    openemr_facility_name: str | None = None,
) -> ProviderMapping:
    """
    Create a new provider mapping linking an OpenEMR provider to a Zoom user.

    Raises:
        ValueError: If account not found, mapping already exists, or the provider
        doesn't have a paid Zoom license - basic is not accepted
    """
    # Validate Zoom license type
    if zoom_user_type == 1:
        raise ValueError(
            f"Zoom user {zoom_user_email} has a Basic (free) license. "
            "A paid Zoom license is required for telehealth features. "
            "Please assign a Licensed seat to this user in the Zoom admin portal."
        )
    
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    # Check for duplicate — same NPI already mapped for this account
    existing = ProviderMapping.query.filter_by(
        zoom_account_id=zoom_account_id,
        openemr_provider_npi=openemr_provider_npi,
        is_active=True
    ).first()
    if existing:
        raise ValueError(
            f"Provider NPI {openemr_provider_npi} is already mapped to "
            f"{existing.zoom_user_email} for this account"
        )

    mapping = ProviderMapping(
        zoom_account_id=zoom_account_id,
        openemr_fhir_id=openemr_fhir_id,
        openemr_provider_npi=openemr_provider_npi,
        openemr_provider_id=openemr_provider_id,
        openemr_provider_name=openemr_provider_name,
        openemr_facility_id=openemr_facility_id,
        openemr_facility_name=openemr_facility_name,
        zoom_user_id=zoom_user_id,
        zoom_user_email=zoom_user_email,
        zoom_user_name=zoom_user_name,
        zoom_user_type=zoom_user_type,
        is_active=True
    )

    db.session.add(mapping)
    db.session.commit()

    logger.info(
        f"Provider mapping created: NPI {openemr_provider_npi} "
        f"→ Zoom user {zoom_user_email}"
    )
    return mapping


def _get_provider_mappings(zoom_account_id: str) -> list[ProviderMapping]:
    """
    Get all active provider mappings for a Zoom account.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    return ProviderMapping.query.filter_by(
        zoom_account_id=zoom_account_id,
        is_active=True
    ).all()


def _delete_provider_mapping(zoom_account_id: str, openemr_provider_id: str) -> None:
    """
    Delete a provider mapping by npi.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    mapping = ProviderMapping.query.filter_by(
        openemr_provider_id=openemr_provider_id,
        zoom_account_id=zoom_account_id,
        is_active=True
    ).first()
    if not mapping:
        raise ValueError(f"No active mapping found with NPI {openemr_provider_id}")

    db.session.delete(mapping)
    db.session.commit()
    logger.info(f"Provider mapping for NPI {openemr_provider_id} deleted")
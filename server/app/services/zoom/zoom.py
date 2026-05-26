from __future__ import annotations
from typing import TYPE_CHECKING
import logging
from datetime import datetime
import requests
from .zoom_auth import get_zoom_token, make_zoom_api_request
from app.services.openemr import get_patient
from app.models import ZoomAccount

if TYPE_CHECKING: 
    from ..openemr.appointments.appointment_processor import AppointmentMatch

logger = logging.getLogger(__name__)

ZOOM_API_BASE_URL = "https://api.zoom.us/v2"

def get_zoom_users(
    zoom_account: ZoomAccount,
    search: str | None = None
) -> list[dict]:
    """
    Fetch users from the Zoom account.
    Used to populate the provider mapping dropdown in the React config page.

    Args:
        zoom_account: ZoomAccount to authenticate with
        search: Optional email or name search string

    Returns: List of simplified user dicts
    """
    token = get_zoom_token(zoom_account)

    params = {
        "page_size": 100,
        "status": "active"
    }
    if search:
        params["search_key"] = search

    response = requests.get(
        f"{ZOOM_API_BASE_URL}/users",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        params=params,
        timeout=10
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "zoom_user_id": user.get("id"),
            "email": user.get("email"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "display_name": user.get("display_name"),
            "type": user.get("type"),
            "status": user.get("status"),
            # IANA timezone string from the Zoom user profile (e.g. 'America/Denver').
            # Cached on ProviderMapping.zoom_user_timezone when this user is
            # mapped to an OpenEMR provider so meeting creation can schedule
            # at the provider's local time instead of the account-wide TZ.
            "timezone": user.get("timezone"),
        }
        for user in data.get("users", [])
    ]


def create_zoom_meeting(match: AppointmentMatch) -> dict:
    """
    Create a scheduled Zoom meeting for a matched appointment event.

    Uses the provider's Zoom user ID as the meeting host. Start time is
    built from the appointment date/time and the account's configured timezone.

    Args:
        match: AppointmentMatch containing zoom_account, provider_mapping,
               and the validated appointment payload.

    Returns:
        dict with keys:
            meeting_id  — Zoom meeting ID (integer as string)
            start_url   — Host/alternative host start URL (expires 90 days for API users)
            join_url    — Patient join URL (does not expire)
            topic       — Meeting topic as created in Zoom

    Raises:
        requests.HTTPError: If the Zoom API returns a non-2xx response.
        ValueError: If required payload fields are missing.
    """
    account = match.zoom_account
    mapping = match.provider_mapping
    payload = match.payload

    # --- 1. Validate required fields ---
    appointment_date = payload.get("appointment_date")  # YYYYMMDD
    appointment_time = payload.get("appointment_time")  # HH:MM
    if not appointment_date or not appointment_time:
        raise ValueError(
            f"Missing appointment_date or appointment_time in payload for eid={payload.get('eid')}"
        )

    # --- 2. Build start_time string ---
    # Zoom expects ISO 8601 local time alongside a separate timezone field:
    # "start_time": "2026-04-20T10:00:00", "timezone": "America/Denver"
    # We do NOT convert to UTC — Zoom handles the conversion using the timezone field.
    start_dt = None
    for fmt in ("%Y%m%d %H:%M", "%Y-%m-%d %H:%M"):
        try:
            start_dt = datetime.strptime(
                f"{appointment_date} {appointment_time}",
                fmt
            )
            break
        except ValueError:
            continue

    if start_dt is None:
        raise ValueError(
            f"Could not parse appointment datetime for eid={payload.get('eid')}: "
            f"date={appointment_date} time={appointment_time}"
        )
    start_time_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")

        # --- 3. Build meeting topic ---
    # Format: "Telehealth: {provider_name} | {patient_last_name} | {title}"
    # Falls back gracefully if any component is missing.
    #
    # Provider name comes from ProviderMapping.openemr_provider_name.
    # Patient last name requires a FHIR lookup using pid from the payload.
    # Title comes from payload['title'] (form_title from OpenEMR).
 
    provider_name = mapping.openemr_provider_name or "Provider"
 
    # FHIR Patient lookup for last name
    patient_last_name = None
    pid = payload.get("pid")
    if pid:
        try:
            patient = get_patient(account, pid)
            if patient:
                patient_last_name = patient.get("last_name")
        except Exception as e:
            # Non-fatal — degrade gracefully to topic without patient name
            logger.warning(
                f"zoom.create_meeting | FHIR patient lookup failed for pid={pid} "
                f"eid={payload.get('eid')}: {e}"
            )
 
    title = payload.get("title")
 
    # Build topic components, filtering out any that are empty
    topic_parts = ["Telehealth"]
    if provider_name:
        topic_parts.append(provider_name)
    if patient_last_name:
        topic_parts.append(patient_last_name)
    if title:
        topic_parts.append(title)
 
    topic = " | ".join(topic_parts)
 
    # Zoom topic max length is 200 characters — truncate if needed
    if len(topic) > 200:
        topic = topic[:197] + "..."
 

    # --- 4. Build duration ---
    # Use duration from payload if present, otherwise default to 30 minutes.
    duration_minutes = payload.get("duration_minutes", 30)
    if not isinstance(duration_minutes, int) or duration_minutes <= 0:
        duration_minutes = 30

    # --- 5. Build Zoom API payload ---
    # Provider TZ wins: each Zoom user has a profile timezone, cached on
    # ProviderMapping.zoom_user_timezone at mapping creation. AccountConfig
    # remains as a fallback for mappings created before that field existed
    # or for Zoom users with no profile TZ set.
    meeting_timezone = mapping.zoom_user_timezone or account.config.timezone
    meeting_payload = {
        "topic": topic,
        "agenda": payload.get("comments") or "",
        # type 2 = scheduled meeting (not instant, not recurring)
        "type": 2,
        "start_time": start_time_str,
        "duration": duration_minutes,
        "timezone": meeting_timezone,
        "settings": {
            "host_video": False,
            "participant_video": False,
            "join_before_host": False,
            "mute_upon_entry": True,
            "waiting_room": True,
            "waiting_room_options": {
                "mode": "custom",
                "who_goes_to_waiting_room": "users_not_in_account"
            },
        },
    }

    # --- 6. Add alternative host if set on the mapping ---
    # Currently always None until the config UI is built.
    # When populated, Zoom sends them a host link and they can start the meeting - Such as an MA or Nurse rooming the patient for the provider.
    if mapping.default_alternative_host_email:
        meeting_payload["settings"]["alternative_hosts"] = (
            mapping.default_alternative_host_email
        )

    logger.info(
        f"zoom.create_meeting | Creating meeting for eid={payload.get('eid')} "
        f"provider={mapping.zoom_user_id} start={start_time_str} "
        f"tz={meeting_timezone} (provider_tz={mapping.zoom_user_timezone or 'none'}, "
        f"account_tz={account.config.timezone}) duration={duration_minutes}min"
    )

    # --- 7. Call Zoom API ---
    response = make_zoom_api_request(
        method="POST",
        endpoint=f"/users/{mapping.zoom_user_id}/meetings",
        zoom_account=account,
        json=meeting_payload,
    )

    meeting_id = str(response.get("id", ""))
    start_url = response.get("start_url", "")
    join_url = response.get("join_url", "")

    logger.info(
        f"zoom.create_meeting | Meeting created: id={meeting_id} "
        f"eid={payload.get('eid')}"
    )

    return {
        "meeting_id": meeting_id,
        "start_url": start_url,
        "join_url": join_url,
        "topic": response.get("topic", topic),
    }


def get_zoom_meeting(zoom_account: ZoomAccount, meeting_id: str) -> dict | None:
    """
    Fetch a Zoom meeting by ID.
 
    Returns the meeting dict if it exists, None if it has been deleted
    (Zoom returns 404 for deleted meetings).
 
    Args:
        zoom_account: ZoomAccount to authenticate with
        meeting_id:   Zoom meeting ID string
 
    Returns:
        Meeting dict from Zoom API, or None if not found.
    """
    try:
        return make_zoom_api_request(
            method="GET",
            endpoint=f"/meetings/{meeting_id}",
            zoom_account=zoom_account,
        )
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            logger.info(
                f"zoom.get_meeting | Meeting {meeting_id} not found in Zoom (likely deleted)"
            )
            return None
        raise
 
 
def delete_zoom_meeting(zoom_account: ZoomAccount, meeting_id: str) -> bool:
    """
    Delete a Zoom meeting by ID.
 
    Used when an OpenEMR appointment is deleted — removes the corresponding
    Zoom meeting so the provider doesn't see a ghost meeting in their calendar.
 
    Args:
        zoom_account: ZoomAccount to authenticate with
        meeting_id:   Zoom meeting ID string
 
    Returns:
        True if deleted successfully, False if meeting was already gone.
    """
    try:
        make_zoom_api_request(
            method="DELETE",
            endpoint=f"/meetings/{meeting_id}",
            zoom_account=zoom_account,
        )
        logger.info(f"zoom.delete_meeting | Meeting {meeting_id} deleted")
        return True
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            logger.info(
                f"zoom.delete_meeting | Meeting {meeting_id} already deleted in Zoom"
            )
            return False
        raise


def update_zoom_meeting(
    zoom_account: ZoomAccount,
    meeting_id: str,
    match: "AppointmentMatch"
) -> None:
    """
    Update an existing Zoom meeting with new appointment details.

    Called when an OpenEMR appointment is updated and a MeetingRecord
    already exists. Updates all four mutable fields unconditionally.

    Args:
        zoom_account: ZoomAccount to authenticate with
        meeting_id:   Zoom meeting ID string
        match:        AppointmentMatch with updated payload and provider mapping
    """
    mapping = match.provider_mapping
    payload = match.payload

    appointment_date = payload.get("appointment_date")
    appointment_time = payload.get("appointment_time")

    # Parse start time — same logic as create_zoom_meeting
    start_dt = None
    for fmt in ("%Y%m%d %H:%M", "%Y-%m-%d %H:%M"):
        try:
            start_dt = datetime.strptime(
                f"{appointment_date} {appointment_time}",
                fmt
            )
            break
        except ValueError:
            continue

    if start_dt is None:
        raise ValueError(
            f"Could not parse appointment datetime for update: "
            f"date={appointment_date} time={appointment_time}"
        )

    start_time_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")

    # Rebuild topic — same logic as create_zoom_meeting
    provider_name = mapping.openemr_provider_name or "Provider"
    patient_last_name = None
    pid = payload.get("pid")
    if pid:
        try:
            patient = get_patient(zoom_account, pid)
            if patient:
                patient_last_name = patient.get("last_name")
        except Exception as e:
            logger.warning(
                f"zoom.update_meeting | FHIR patient lookup failed for pid={pid}: {e}"
            )

    title = payload.get("title")
    topic_parts = ["Telehealth"]
    if provider_name:
        topic_parts.append(provider_name)
    if patient_last_name:
        topic_parts.append(patient_last_name)
    if title:
        topic_parts.append(title)
    topic = " | ".join(topic_parts)
    if len(topic) > 200:
        topic = topic[:197] + "..."

    duration_minutes = payload.get("duration_minutes", 30)
    if not isinstance(duration_minutes, int) or duration_minutes <= 0:
        duration_minutes = 30

    # Provider TZ wins, account TZ is fallback. See create_zoom_meeting for rationale.
    meeting_timezone = mapping.zoom_user_timezone or zoom_account.config.timezone
    update_payload = {
        "topic": topic,
        "start_time": start_time_str,
        "duration": duration_minutes,
        "timezone": meeting_timezone,
        "agenda": payload.get("comments") or "",
    }

    logger.info(
        f"zoom.update_meeting | Updating meeting {meeting_id} "
        f"start={start_time_str} tz={meeting_timezone} "
        f"(provider_tz={mapping.zoom_user_timezone or 'none'}, "
        f"account_tz={zoom_account.config.timezone}) duration={duration_minutes}min"
    )

    make_zoom_api_request(
        method="PATCH",
        endpoint=f"/meetings/{meeting_id}",
        zoom_account=zoom_account,
        json=update_payload,
    )

    logger.info(f"zoom.update_meeting | Meeting {meeting_id} updated successfully")


def get_zoom_clinical_note(zoom_account: ZoomAccount, note_id: str) -> dict | None:
    """
    etrieve clinical note content from Zoom Healthcare API.

    GET /clinical_notes/notes/{note_id}

    Returns the full note dict including note_content, or None if not found.
    """
    try:
        result = make_zoom_api_request(
            "GET",
            f"/clinical_notes/notes/{note_id}",
            zoom_account
        )
        content = result.get("note_content") or ""
        stripped_length = len(content.strip())
        logger.info(
            f"zoom.get_clinical_note | Retrieved note_id={note_id} "
            f"is_completed={result.get('is_note_completed')} "
            f"content_length={len(content)} stripped_length={stripped_length} "
            f"content_blank={stripped_length == 0}"
        )
        return result
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"zoom.get_clinical_note | Note {note_id} not found")
            return None
        logger.error(f"zoom.get_clinical_note | Failed to retrieve note {note_id}: {e}")
        raise

def mark_zoom_note_completed(zoom_account: ZoomAccount, note_id: str) -> bool:
    """
    Mark a Zoom clinical note as completed.

    PATCH /clinical_notes/notes/{note_id} with is_note_completed: true.
    Called after the provider eSigns and locks the form in OpenEMR.

    Args:
        zoom_account: The ZoomAccount to use for authentication
        note_id:      Zoom note ID string

    Returns:
        True if successful, False on error
    """
    try:
        make_zoom_api_request(
            "PATCH",
            f"/clinical_notes/notes/{note_id}",
            zoom_account,
            json={"is_note_completed": True}
        )
        logger.info(f"zoom.mark_zoom_note_completed | note_id={note_id} marked completed")
        return True
    except Exception as e:
        logger.error(f"zoom.mark_zoom_note_completed | Failed for note_id={note_id}: {e}")
        return False
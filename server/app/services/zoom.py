from __future__ import annotations
from typing import TYPE_CHECKING
import base64
import time
import logging
from datetime import datetime, timezone

import requests
from flask import current_app

from app.extensions import db
from app.models import ZoomAccount

if TYPE_CHECKING: 
    from .appointment_processor import AppointmentMatch


logger = logging.getLogger(__name__)

ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_API_BASE_URL = "https://api.zoom.us/v2"


def _build_basic_auth_header(client_id: str, client_secret: str) -> str:
    """
    Zoom S2S HTTP Basic Auth.
    """
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return f"Basic {encoded}"

def _fetch_zoom_token(zoom_account: ZoomAccount, refresh: bool = False) -> tuple[str, int, str]:
    """
    Fetch a fresh Zoom token and store it on the account record.
    Internal only — callers should use get_zoom_token()
    """
    response = requests.post(
        ZOOM_TOKEN_URL,
        params={
            "grant_type": "account_credentials",
            "account_id": zoom_account.account_id,
        },
        headers={
            "Authorization": _build_basic_auth_header(zoom_account.client_id, zoom_account.client_secret),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=10
    )
    response.raise_for_status()
    data = response.json()
    
    access_token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    scope = data.get("scope", "")

    zoom_account.zoom_access_token = access_token
    zoom_account.zoom_token_expires_at = datetime.fromtimestamp(time.time() + expires_in, tz=timezone.utc)
    
    refreshed = "force refreshed" if refresh else "fetched"

    db.session.commit()
    logger.info(
        f"Zoom token {refreshed} and cached for account {zoom_account.account_id}, "
        f"expires in {expires_in}s, scopes: {scope}"
    )

    return access_token, expires_in, scope
    

def validate_zoom_credentials(
    zoom_account: ZoomAccount
) -> bool:
    """
    Validate Zoom S2S credentials by attempting to fetch a token.
    Used during registration to verify credentials before storing them.

    Returns True if credentials are valid, False otherwise.
    """
    try:
        _, _, scope = _fetch_zoom_token(zoom_account)
        logger.info(
            f"Zoom credentials validated for account {zoom_account.account_id}, "
            f"scopes: {scope}"
        )
        return True
    except requests.HTTPError as e:
        logger.warning(
            f"Zoom credential validation failed for account {zoom_account.account_id}: {e}"
        )
        return False
    except requests.RequestException as e:
        logger.error(f"Network error validating Zoom credentials: {e}")
        raise


def get_zoom_token(zoom_account: ZoomAccount, force_refresh: bool = False) -> str:
    """
    Get a valid Zoom access token for the given account, using the DB cache.

    This is the function the rest of the app calls when it needs to make
    Zoom API requests. It handles caching and refresh transparently.

    The cache lives in the ZoomAccount row itself — no separate token table.
    We check if the cached token has more than 300 seconds (5 min) left before expiry.
    If not, we fetch a fresh one and update the DB.

    Args:
        zoom_account: The ZoomAccount ORM object (must be within a DB session)
        force_refresh: If True, always fetch a fresh token regardless of cache

    Returns: A valid Bearer token string
    """
    now = datetime.now(timezone.utc)

    # Check if cached token is still valid (with 300 second buffer)
    if not force_refresh and zoom_account.zoom_access_token and zoom_account.zoom_token_expires_at:
        expires_at = zoom_account.zoom_token_expires_at
        # Ensure timezone awareness for comparison
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        seconds_remaining = (expires_at - now).total_seconds()
        if seconds_remaining > 300:
            logger.debug(
                f"Using cached Zoom token for account {zoom_account.account_id} "
                f"({int(seconds_remaining)}s remaining. Will refresh with 300s remaining)"
            )
            return zoom_account.zoom_access_token

    # Fetch fresh token
    logger.info(f"Fetching fresh Zoom token for account {zoom_account.account_id}")

    access_token, _, _  = _fetch_zoom_token(zoom_account, refresh=force_refresh)

    return access_token


def make_zoom_api_request(
    method: str,
    endpoint: str,
    zoom_account: ZoomAccount,
    **kwargs
) -> dict:
    """
    Make an authenticated request to the Zoom API.

    Automatically handles token fetching and attaches the Bearer token.
    Pass any additional requests kwargs (json=, params=, etc.) through **kwargs.

    Example:
        note = make_zoom_api_request("GET", f"/clinical_notes/notes/{note_id}", account)

    Returns: Parsed JSON response dict
    Raises: requests.HTTPError on non-2xx responses
    """
    token = get_zoom_token(zoom_account)
    url = f"{ZOOM_API_BASE_URL}{endpoint}"

    response = requests.request(
        method=method.upper(),
        url=url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=10,
        **kwargs
    )

    response.raise_for_status()
    if response.status_code == 204 or not response.content:
        return {}

    return response.json()


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
            from app.services.openemr import get_patient
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
    meeting_payload = {
        "topic": topic,
        "agenda": payload.get("comments") or "",
        # type 2 = scheduled meeting (not instant, not recurring)
        "type": 2,
        "start_time": start_time_str,
        "duration": duration_minutes,
        # Account timezone — set during registration, defaults to America/New_York if not configured at app registration.
        "timezone": account.timezone,
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
        f"tz={account.timezone} duration={duration_minutes}min"
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
            from app.services.openemr import get_patient
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

    update_payload = {
        "topic": topic,
        "start_time": start_time_str,
        "duration": duration_minutes,
        "timezone": zoom_account.timezone,
        "agenda": payload.get("comments") or "",
    }

    logger.info(
        f"zoom.update_meeting | Updating meeting {meeting_id} "
        f"start={start_time_str} tz={zoom_account.timezone} duration={duration_minutes}min"
    )

    make_zoom_api_request(
        method="PATCH",
        endpoint=f"/meetings/{meeting_id}",
        zoom_account=zoom_account,
        json=update_payload,
    )

    logger.info(f"zoom.update_meeting | Meeting {meeting_id} updated successfully")
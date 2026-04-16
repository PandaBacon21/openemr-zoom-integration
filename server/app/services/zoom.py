import base64
import time
import logging
from datetime import datetime, timezone

import requests
from flask import current_app

from app.extensions import db
from app.models import ZoomAccount

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
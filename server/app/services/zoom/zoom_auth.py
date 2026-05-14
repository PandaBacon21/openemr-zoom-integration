from __future__ import annotations
import base64
import time
import logging
from datetime import datetime, timezone
import requests
from app.extensions import db
from app.models import ZoomAccount
from app.services.audit import write_audit_log


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
    try:
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
    except Exception as e:
        detail: dict = {}
        if isinstance(e, requests.HTTPError):
            if e.response is not None:
                detail["status_code"] = e.response.status_code
                try:
                    body = e.response.json()
                    detail["zoom_error"] = body.get("reason") or body.get("error")
                except Exception:
                    pass
                detail["body_snippet"] = e.response.text[:200]
        elif isinstance(e, requests.RequestException):
            detail["stage"] = "network"
        else:
            detail["stage"] = "fetch"
        write_audit_log(
            event_type="zoom.token_refresh_failed",
            success=False,
            zoom_account_id=zoom_account.account_id,
            error_message=str(e),
            detail=detail,
        )
        raise
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
        write_audit_log(
            event_type="zoom.credentials_validated",
            success=True,
            zoom_account_id=zoom_account.account_id,
            detail={"scopes": scope},
        )
        return True
    except requests.HTTPError as e:
        logger.warning(
            f"Zoom credential validation failed for account {zoom_account.account_id}: {e}"
        )
        status = e.response.status_code if e.response is not None else None
        write_audit_log(
            event_type="zoom.credentials_validation_failed",
            success=False,
            zoom_account_id=zoom_account.account_id,
            error_message=str(e),
            detail={"status_code": status},
        )
        return False
    except requests.RequestException as e:
        logger.error(f"Network error validating Zoom credentials: {e}")
        # _fetch_zoom_token already wrote zoom.token_refresh_failed; we re-raise
        # without a separate validation audit so the caller can react.
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
import time
import uuid
import logging
import jwt
import requests
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from flask import current_app
from .jwks import load_private_key

logger = logging.getLogger(__name__)

# def _retrieve_scopes() -> list[str]: 
#     return current_app.config["OPENEMR_SCOPES"]

def build_client_assertion(
    client_id: str,
    audience: str,
    key_path: str,
    key_id: str 
) -> str:
    """
    Build and sign a JWT client assertion for SMART Backend Services.
    This is what we POST to OpenEMR's token endpoint to prove our identity.
    """
    private_key = load_private_key(key_path)
    assert isinstance(private_key, RSAPrivateKey)

    now = int(time.time())

    payload = {
        "iss": client_id,           # Issuer — client ID in OpenEMR
        "sub": client_id,           # Subject — same as issuer for backend services
        "aud": audience,            # Audience — the token endpoint we're calling
        "jti": str(uuid.uuid4()),   # Unique ID 
        "iat": now,                 # Issued at
        "exp": now + 300,           # Expires in 5 minutes
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS384",
        headers={"kid": key_id} 
    )

    return token


def exchange_assertion_for_token(
    client_id: str,
    token_endpoint: str,
    audience: str,
    scopes: list[str],
    key_path: str, 
    key_id: str
) -> tuple[str, int] :
    """
    POST the signed client assertion to OpenEMR's token endpoint.
    Returns the access token string.
    """
    assertion = build_client_assertion(client_id, audience, key_path, key_id)

    response = requests.post(
        token_endpoint,
        data={
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
            "scope": " ".join(scopes),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10
    )

    response.raise_for_status()
    data = response.json()

    return data["access_token"], data.get("expires_in", 300)

def get_openemr_token(zoom_account, force_refresh: bool = False) -> str:
    """
    Get a valid OpenEMR access token
    Token is stored per-account on the ZoomAccount model

    Args:
    zoom_account: ZoomAccount ORM object (must be within a DB session)
    force_refresh: If True, always fetch fresh regardless of cache

    Returns: A valid Bearer token string
    Raises: requests.HTTPError if token fetch fails (e.g. client not yet
            enabled in OpenEMR — caller should handle this gracefully)
    """
    from app.extensions import db

    now = datetime.now(timezone.utc)

    # Return cached token if still valid (with 30 second buffer)
    if not force_refresh and zoom_account.openemr_access_token and zoom_account.openemr_token_expires_at:
        expires_at = zoom_account.openemr_token_expires_at
        if expires_at.tzinfo is None: 
            expires_at = expires_at.replace(tzinfo=timezone.utc)

            seconds_remaining = (expires_at - now).total_seconds()
            if seconds_remaining > 30:
                logger.debug(
                f"Using cached OpenEMR token for account {zoom_account.account_id} "
                f"({int(seconds_remaining)}s remaining)"
                )
                return zoom_account.openemr_access_token

    # Need a fresh token
    logger.info(f"Fetching fresh OpenEMR token for account {zoom_account.account_id}")

    base_url = current_app.config["OPENEMR_BASE_URL"]
    public_url = current_app.config["OPENEMR_PUBLIC_URL"]
    token_endpoint = f"{base_url}/oauth2/default/token"
    audience = f"{public_url}/oauth2/default/token"
    scopes = current_app.config["OPENEMR_SCOPES"]

    access_token, expires_in = exchange_assertion_for_token(
        zoom_account.openemr_client_id, token_endpoint, audience, scopes, zoom_account.private_key_path, zoom_account.kid
    )

    # Update cache on the account record
    zoom_account.openemr_access_token = access_token
    zoom_account.openemr_token_expires_at = datetime.fromtimestamp(
        time.time() + expires_in, tz=timezone.utc
    )
    db.session.commit()

    logger.info(
        f"OpenEMR token refreshed for account {zoom_account.account_id}, "
        f"expires in {expires_in}s"
    )

    return access_token
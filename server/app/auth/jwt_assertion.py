import time
import uuid
import jwt
import requests
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from flask import current_app
from .jwks import load_private_key

# Module-level token cache — survives across requests within one process
_token_cache = {
    "access_token": None,
    "expires_at": 0
}


def build_client_assertion(
    client_id: str,
    token_endpoint: str,
    key_path: str,
    key_id: str = "zoomly-key-1"
) -> str:
    """
    Build and sign a JWT client assertion for SMART Backend Services.
    This is what we POST to OpenEMR's token endpoint to prove our identity.
    """
    private_key = load_private_key(key_path)
    assert isinstance(private_key, RSAPrivateKey), "Expected RSA private key"

    now = int(time.time())

    payload = {
        "iss": client_id,       # Issuer — who we are (our client ID in OpenEMR)
        "sub": client_id,       # Subject — same as issuer for backend services
        "aud": token_endpoint,  # Audience — the token endpoint we're calling
        "jti": str(uuid.uuid4()),  # Unique ID — prevents replay attacks
        "iat": now,             # Issued at
        "exp": now + 300,       # Expires in 5 minutes
    }

    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": key_id}  # Tells OpenEMR which key in our JWKS to use
    )

    return token


def exchange_assertion_for_token(
    client_id: str,
    token_endpoint: str,
    scopes: list[str],
    key_path: str
) -> tuple[str, int] :
    """
    POST the signed client assertion to OpenEMR's token endpoint.
    Returns the access token string.
    """
    assertion = build_client_assertion(client_id, token_endpoint, key_path)

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


def get_openemr_token(force_refresh: bool = False) -> str:
    """
    Get a valid OpenEMR access token, using the cache if available.
    This is the function the rest of the app calls — it handles
    caching and refresh transparently.
    """
    global _token_cache
    now = int(time.time())

    # Return cached token if still valid (with 30 second buffer)
    if not force_refresh and _token_cache["access_token"]:
        if now < (_token_cache["expires_at"] - 30):
            return _token_cache["access_token"]

    # Need a fresh token
    client_id = current_app.config["OPENEMR_CLIENT_ID"]
    key_path = current_app.config["JWKS_KEY_PATH"]
    base_url = current_app.config["OPENEMR_BASE_URL"]
    token_endpoint = f"{base_url}/oauth2/default/token"

    scopes = [
        "system/Patient.read",
        "system/Appointment.read",
        "system/Appointment.write",
        "system/Encounter.read",
        "system/Encounter.write",
    ]

    access_token, expires_in = exchange_assertion_for_token(
        client_id, token_endpoint, scopes, key_path
    )

    # Cache it
    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = now + expires_in

    return access_token
import base64
import jwt
import hashlib
from werkzeug.security import generate_password_hash
from flask import current_app
from app.models import ZoomAccount
from app.extensions import db
import logging

logger = logging.getLogger(__name__)


def set_ehr_context_credentials(account: ZoomAccount, ehr_context_username: str, ehr_context_password: str) -> ZoomAccount:
    account.ehr_context_username = ehr_context_username
    account.ehr_context_password_hash = generate_password_hash(ehr_context_password)
    logger.info(f"ehr_context.set_credentials | Set EHR Context credentials for account={account.account_id}")
    return account


def _generate_tenant_id(account_id: str, client_id: str) -> str:
    """
    Generate a unique tenant identifier for a Zoom account.
 
    Derived from SHA256(account_id + client_id), truncated to 10 hex chars.
    Used as the X-Tenant-ID value Zoom sends in EHR integration requests.
 
    This is deterministic — the same account_id + client_id always produces
    the same tenant_id, so it can be regenerated if needed.
 
    Args:
        account_id: Zoom account ID string
        client_id:  Zoom OAuth client ID string
 
    Returns:
        10-character lowercase hex string
    """
    raw = f"{account_id}{client_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


def _get_account_by_tenant(tenant_id: str) -> ZoomAccount | None:
    """Look up an active ZoomAccount by tenant_id."""
    return ZoomAccount.query.filter_by(
        tenant_id=tenant_id,
        is_active=True
    ).first()


def _verify_basic_auth(authorization_header: str, account: ZoomAccount) -> bool:
    """
    Verify a Basic Auth header against the account's stored credentials.

    Basic Auth format: "Basic <base64(username:password)>"
    Password is verified against the bcrypt hash stored on the account.
    """
    if not authorization_header or not authorization_header.startswith("Basic "):
        return False

    try:
        encoded = authorization_header.split(" ", 1)[1]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return False

    if username != account.ehr_context_username:
        return False

    if not account.ehr_context_password_hash:
        return False

    from werkzeug.security import check_password_hash
    return check_password_hash(account.ehr_context_password_hash, password)


def _verify_bearer_jwt(authorization_header: str, tenant_id: str) -> bool:
    """
    Verify a Bearer JWT from the Authorization header.

    Checks:
      - Valid JWT signature (signed with SECRET_KEY)
      - Not expired
      - sub claim matches tenant_id
      - tid claim matches tenant_id (double check)
    """
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return False

    token = authorization_header.split(" ", 1)[1]
    secret = current_app.config.get("SECRET_KEY")
    if not secret: 
        logger.warning("ehr_context.verify_jwt | SECRET_KEY not configured on server")
        return False
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.warning("ehr_context | JWT expired")
        return False
    except jwt.InvalidTokenError as e:
        logger.warning(f"ehr_context | Invalid JWT: {e}")
        return False

    if payload.get("sub") != tenant_id:
        logger.warning(
            f"ehr_context | JWT sub mismatch: expected={tenant_id} got={payload.get('sub')}"
        )
        return False

    if payload.get("tid") != tenant_id:
        logger.warning(
            f"ehr_context | JWT tid mismatch: expected={tenant_id} got={payload.get('tid')}"
        )
        return False

    return True

"""Outbound calls from OpenEMR to Zoom Contact Center's Epic CTI API."""

import logging
from dataclasses import dataclass
from urllib.parse import quote, urlencode

import requests
from flask import current_app

from app.auth.jwt_assertion import build_client_assertion
from app.services.epic.constants import EPIC_KEY_VERSION, EPIC_PATH_SLUG


logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 10


class OutboundZccError(Exception):
    """Raised when an outbound ZCC request cannot be completed."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


class OutboundZccUpstreamError(OutboundZccError):
    """Raised when ZCC returns a non-2xx response."""

    def __init__(self, status_code: int, body_snippet: str):
        super().__init__("upstream_error", f"ZCC returned HTTP {status_code}")
        self.status_code = status_code
        self.body_snippet = body_snippet


@dataclass
class OutboundZccResult:
    status_code: int
    url: str
    body_snippet: str
    phone_system_call_id: str | None = None


def initiate_call(
    account,
    phone_number: str,
    agent_id: str,
    epic_call_id: str,
) -> OutboundZccResult:
    """Ask ZCC to initiate an outbound call for an Epic/ZCC agent."""
    phone = str(phone_number or "").strip()
    if not phone:
        raise OutboundZccError("missing_phone", "phone is required")

    agent = str(agent_id or "").strip()
    if not agent:
        raise OutboundZccError("missing_agent_id", "agent_id is required")

    _validate_account_config(account)
    url = build_initiate_call_url(account)
    jku = _build_jku_url(account)
    iss = _build_issuer_url(account)
    try:
        assertion = build_client_assertion(
            client_id=account.epic_zcc_client_id,
            audience=url,
            key_path=account.private_key_path,
            key_id=account.epic_kid,
            jku=jku,
            issuer=iss,
        )
    except FileNotFoundError as e:
        raise OutboundZccError("missing_private_key", str(e)) from e
    body = build_initiate_call_body(phone, agent, epic_call_id)

    try:
        response = requests.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {assertion}",
                "Content-Type": "application/json",
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        logger.error(
            "epic.outbound_zcc | initiate-call request failed "
            f"account_id={account.account_id}: {e}",
            exc_info=True,
        )
        raise OutboundZccError("request_failed", str(e)) from e

    body_snippet = _safe_body_snippet(response.text, phone)
    if response.status_code < 200 or response.status_code >= 300:
        tracking_id = response.headers.get("X-Zm-Trackingid", "n/a")
        logger.warning(
            "epic.outbound_zcc | initiate-call rejected "
            f"account_id={account.account_id} status={response.status_code} "
            f"tracking_id={tracking_id} body={body_snippet}"
        )
        raise OutboundZccUpstreamError(response.status_code, body_snippet)

    phone_system_call_id: str | None = None
    try:
        phone_system_call_id = response.json().get("PhoneSystemCallID") or None
    except Exception:
        pass

    logger.info(
        "epic.outbound_zcc | initiate-call accepted "
        f"account_id={account.account_id} status={response.status_code} "
        f"phone_system_call_id={phone_system_call_id!r} "
        f"response_body={body_snippet!r}"
    )

    return OutboundZccResult(
        status_code=response.status_code,
        url=url,
        body_snippet=body_snippet,
        phone_system_call_id=phone_system_call_id,
    )


def build_initiate_call_body(
    phone_number: str,
    agent_id: str,
    epic_call_id: str,
) -> dict:
    """Build the Epic.Common.InitiateCall request body.

    Schema per Epic Outgoing CTI Technical Specification:
      PhoneAgentID         — agent's ID in the phone system (Zoom ZCC user ID)
      OriginPhoneExtension — agent's extension (at least one of this or PhoneAgentID required)
      PhoneNumber          — number to dial
      EpicCallID           — our call tracking UUID; ZCC echoes it back as PhoneSystemCallID
                             and includes it as call_id in ReceiveCommunication3
    """
    return {
        "InitiateCallRequest": {
            "PhoneAgentID": agent_id,
            "OriginPhoneExtension": "",
            "PhoneNumber": _normalize_e164(phone_number),
            "EpicCallID": epic_call_id,
        }
    }


def build_initiate_call_url(account) -> str:
    config = account.config
    backend_url = config.epic_zcc_backend_url if config else None
    base = _normalize_backend_base(backend_url)
    endpoint = _append_initiate_call_path(base)
    return f"{endpoint}?{urlencode({'accId': account.account_id})}"


def _validate_account_config(account) -> None:
    if not (account.config and account.config.epic_zcc_backend_url):
        raise OutboundZccError("missing_backend_url", "epic_zcc_backend_url is required")
    if not account.epic_zcc_client_id:
        raise OutboundZccError("missing_client_id", "epic_zcc_client_id is required")
    if not account.epic_kid:
        raise OutboundZccError("missing_epic_kid", "epic_kid is required")
    if not account.private_key_path:
        raise OutboundZccError("missing_private_key", "private_key_path is required")


def _normalize_backend_base(raw: str | None) -> str:
    value = str(raw or "").strip()
    if not value:
        raise OutboundZccError("missing_backend_url", "epic_zcc_backend_url is required")
    if "://" not in value:
        value = f"https://{value}"
    return value.rstrip("/")


def _append_initiate_call_path(base: str) -> str:
    if base.endswith("/v1/cci/epic/initiate-call"):
        return base
    if base.endswith("/v1/cci/epic"):
        return f"{base}/initiate-call"
    return f"{base}/v1/cci/epic/initiate-call"


def _build_issuer_url(account) -> str:
    public_base = current_app.config.get("APP_PUBLIC_URL", "").rstrip("/")
    account_id = quote(account.account_id, safe="")
    return f"{public_base}/zoomly/{account_id}/{EPIC_PATH_SLUG}"


def _build_jku_url(account) -> str:
    public_base = current_app.config.get("APP_PUBLIC_URL", "").rstrip("/")
    account_id = quote(account.account_id, safe="")
    epic_kid = quote(account.epic_kid, safe="")
    return (
        f"{public_base}/zoomly/{account_id}/{EPIC_PATH_SLUG}/oauth2/keys/"
        f"{EPIC_KEY_VERSION}/{epic_kid}"
    )


def _normalize_e164(phone_number: str) -> str:
    """Normalize a US phone string to E.164 (+1XXXXXXXXXX).

    Strips non-digit characters, then:
      - 10 digits → prepend +1
      - 11 digits starting with 1 → prepend +
    """
    digits = "".join(ch for ch in (phone_number or "") if ch.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    raise OutboundZccError(
        "invalid_phone",
        f"Cannot normalize '{phone_number}' to E.164 — expected 10 or 11 US digits",
    )


def _safe_body_snippet(body: str, phone_number: str) -> str:
    snippet = (body or "")[:500]
    phone = str(phone_number or "")
    if phone:
        snippet = snippet.replace(phone, "[phone]")
        digits = "".join(ch for ch in phone if ch.isdigit())
        if digits:
            snippet = snippet.replace(digits, "[phone]")
    return snippet

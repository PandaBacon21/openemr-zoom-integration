"""Parse Epic-ZCC inbound request bodies (JSON).

PatientLookUp(2012) and ReceiveCommunication3: ZCC sends JSON despite Epic's
published XML spec for PatientLookUp. UserID/UserIDType are per-account Epic
background service credentials configured in ZCC — not the individual agent
handling the call.

Faults raised here use Epic's documented fault codes so routes can translate
them straight into the appropriate fault/OperationOutcome envelope.
"""

import json
import logging
import re


logger = logging.getLogger(__name__)


class InvalidEpicRequest(Exception):
    """Raised when an inbound Epic request can't be parsed or is invalid.

    `fault_code` matches one of Epic's documented fault codes so the route can
    return it verbatim inside the relevant response shape.
    """

    def __init__(self, fault_code: str, message: str):
        super().__init__(message)
        self.fault_code = fault_code
        self.message = message


def _normalize_ssn_last4(raw: str | None) -> str | None:
    """Pull the last 4 digits out of a NationalIdentifier value.

    Accepts any of `123-45-6789`, `xxx-xx-6789`, `6789`, or `123456789`.
    Returns None if fewer than 4 digits survive normalization.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 4:
        return None
    return digits[-4:]


def parse_patient_lookup_request(raw_body: bytes) -> dict:
    """Parse an Epic PatientLookUp request body (JSON).

    ZCC sends JSON despite Epic's published XML spec. UserID/UserIDType are
    per-account Epic background service credentials, not the individual agent.

    Raises InvalidEpicRequest with the appropriate Epic fault code if the
    body is malformed, missing the required UserID, or has no search
    criterion among the supported fields (PatientID, DateOfBirth,
    NationalIdentifier, PhoneNumbers).

    Returns:
        {
            "user_id":           str         # Epic background service UserID, required
            "user_id_type":      str | None  # UserIDType — informational
            "patient_id":        str | None  # PatientID
            "patient_id_type":   str | None  # PatientIDType ('EPI', 'MRN', 'FHIR', ...)
            "dob":               str | None  # DateOfBirth (YYYY-MM-DD)
            "ssn_last4":         str | None  # last 4 digits of NationalIdentifier
            "phones":            list[str]   # raw phone strings; normalized in patient_search
        }
    """
    if not raw_body:
        raise InvalidEpicRequest("INVALID-REQUEST", "empty body")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.warning(f"epic.request_parser | malformed PatientLookUp JSON: {e}")
        raise InvalidEpicRequest("INVALID-REQUEST", f"malformed JSON: {e}")

    if not isinstance(payload, dict):
        raise InvalidEpicRequest("INVALID-REQUEST", "body must be a JSON object")

    user_id = _json_text(payload.get("UserID"))
    if not user_id:
        raise InvalidEpicRequest("INVALID-USER", "UserID is required")

    address = payload.get("Address") or {}
    phones: list[str] = []
    if isinstance(address, dict):
        phone_val = address.get("PhoneNumbers")
        if isinstance(phone_val, list):
            phones = [p for p in phone_val if isinstance(p, str) and p.strip()]
        elif isinstance(phone_val, str) and phone_val.strip():
            phones = [phone_val.strip()]

    parsed = {
        "user_id": user_id,
        "user_id_type": _json_text(payload.get("UserIDType")),
        "patient_id": _json_text(payload.get("PatientID")),
        "patient_id_type": _json_text(payload.get("PatientIDType")),
        "dob": _json_text(payload.get("DateOfBirth")),
        "ssn_last4": _normalize_ssn_last4(_json_text(payload.get("NationalIdentifier"))),
        "phones": phones,
    }

    has_criterion = any([
        parsed["patient_id"],
        parsed["dob"],
        parsed["ssn_last4"],
        parsed["phones"],
    ])
    if not has_criterion:
        raise InvalidEpicRequest(
            "INSUFFICIENT-CRITERIA",
            "at least one search criterion is required (PatientID, DateOfBirth, NationalIdentifier, or PhoneNumbers)",
        )

    return parsed


def parse_receive_communication3_request(raw_body: bytes, content_type: str | None = None) -> dict:
    """Parse an Epic ReceiveCommunication3 request body (JSON).

    Returns:
        {
            "recipient_id":       str         # ZCC agent id, required
            "recipient_id_type":  str | None
            "patient_id":         str | None  # LookupID.ID, PatientID, or LookupInformation
            "patient_id_type":    str | None  # LookupID.Type, PatientIDType, or LookupInformationType
            "communication_type": str | None
            "caller_number":      str | None  # CallerPhoneNumber — patient's phone in both directions
            "dialed_number":      str | None  # DialedPhoneNumber — ZCC agent-side number
            "call_id":            str | None
            "lookup_type":        str | None
            "contact_type":       str | None  # "Incoming" or "Outgoing"
        }
    """
    if not raw_body:
        raise InvalidEpicRequest("INVALID-REQUEST", "empty body")

    if content_type and "json" not in content_type.lower():
        logger.info(
            "epic.request_parser | ReceiveCommunication3 content_type=%r parsed as JSON",
            content_type,
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.warning(f"epic.request_parser | malformed ReceiveCommunication3 JSON: {e}")
        raise InvalidEpicRequest("INVALID-REQUEST", f"malformed JSON: {e}")

    if not isinstance(payload, dict):
        raise InvalidEpicRequest("INVALID-REQUEST", "ReceiveCommunication3 body must be a JSON object")

    lookup_id = payload.get("LookupID")
    if not isinstance(lookup_id, dict):
        lookup_id = {}

    patient_id = (
        _json_text(lookup_id.get("ID"))
        or _json_text(payload.get("PatientID"))
        or _json_text(payload.get("LookupInformation"))
    )
    patient_id_type = (
        _json_text(lookup_id.get("Type"))
        or _json_text(payload.get("PatientIDType"))
        or _json_text(payload.get("LookupInformationType"))
    )

    parsed = {
        "recipient_id": _json_text(payload.get("RecipientID")),
        "recipient_id_type": _json_text(payload.get("RecipientIDType")),
        "patient_id": patient_id,
        "patient_id_type": patient_id_type,
        "communication_type": _json_text(payload.get("CommunicationType")),
        "caller_number": _json_text(payload.get("CallerPhoneNumber")),
        "dialed_number": _json_text(payload.get("DialedPhoneNumber")),
        "call_id": _json_text(payload.get("CallID")),
        "lookup_type": _json_text(payload.get("LookupType")),
        "contact_type": _json_text(payload.get("ContactType")),
    }

    if not parsed.get("recipient_id"):
        raise InvalidEpicRequest("NO-USER-ID", "RecipientID is required")

    return parsed


def _json_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None

"""Parse Epic-ZCC inbound request bodies.

PatientLookUp(2012) uses a SOAP-style XML document under the
`urn:Epic-com:EMPI.2012.Services.Patient` namespace. We accept the full Epic
schema but only act on the fields Zoomly's IVR-driven CTI flow actually
populates: PatientID + PatientIDType, DateOfBirth, NationalIdentifier (SSN),
phone numbers, and the required UserID identifying which ZCC agent is doing
the lookup.

ReceiveCommunication3 uses JSON in Epic's published docs. We parse that as
the primary contract and keep a small XML fallback for integration resilience.

Faults raised here use Epic's documented fault codes so routes can translate
them straight into the appropriate fault/OperationOutcome envelope.
"""

import json
import logging
import re
from xml.etree import ElementTree as ET

from .constants import EPIC_XML_NAMESPACE


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


_NS = {"e": EPIC_XML_NAMESPACE}


def _text(root: ET.Element, path: str) -> str | None:
    """Find a single element under the Epic namespace and return its stripped text, or None."""
    el = root.find(path, _NS)
    if el is None or el.text is None:
        return None
    text = el.text.strip()
    return text or None


def _phones(root: ET.Element) -> list[str]:
    """Collect all phone numbers under the Address.PhoneNumbers branch.

    Epic wraps phone strings in the MS Serialization Arrays namespace inside
    the PhoneNumbers container. We use a wildcard child match so we don't
    have to hardcode that secondary namespace.
    """
    container = root.find("e:Address/e:PhoneNumbers", _NS)
    if container is None:
        return []
    phones: list[str] = []
    for child in container:
        if child.text:
            normalized = child.text.strip()
            if normalized:
                phones.append(normalized)
    return phones


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


def parse_patient_lookup_request(xml_bytes: bytes) -> dict:
    """Parse an Epic PatientLookUp request body.

    Raises InvalidEpicRequest with the appropriate Epic fault code if the
    body is malformed, missing the required UserID, or has no search
    criterion among the supported fields (PatientID, DateOfBirth,
    NationalIdentifier, PhoneNumbers).

    Returns:
        {
            "user_id":           str         # OpenEMR user id (UserID), required
            "user_id_type":      str | None  # UserIDType ('EXTERNAL', etc.) — informational
            "patient_id":        str | None  # PatientID
            "patient_id_type":   str | None  # PatientIDType ('EPI', 'MRN', 'FHIR', ...)
            "dob":               str | None  # DateOfBirth (YYYY-MM-DD)
            "ssn_last4":         str | None  # last 4 digits of NationalIdentifier
            "phones":            list[str]   # raw phone strings; normalized in patient_search
        }
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.warning(f"epic.request_parser | malformed XML: {e}")
        raise InvalidEpicRequest("INVALID-REQUEST", f"malformed XML: {e}")

    # Strip the namespace from the root tag for the check; Epic always uses
    # <PatientLookup> as the root.
    if not root.tag.endswith("}PatientLookup") and root.tag != "PatientLookup":
        raise InvalidEpicRequest("INVALID-REQUEST", f"unexpected root element {root.tag!r}")

    user_id = _text(root, "e:UserID")
    if not user_id:
        raise InvalidEpicRequest("INVALID-USER", "UserID is required")

    parsed = {
        "user_id": user_id,
        "user_id_type": _text(root, "e:UserIDType"),
        "patient_id": _text(root, "e:PatientID"),
        "patient_id_type": _text(root, "e:PatientIDType"),
        "dob": _text(root, "e:DateOfBirth"),
        "ssn_last4": _normalize_ssn_last4(_text(root, "e:NationalIdentifier")),
        "phones": _phones(root),
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
            "at least one of PatientID, DateOfBirth, NationalIdentifier, or PhoneNumbers is required",
        )

    return parsed


def parse_receive_communication3_request(raw_body: bytes, content_type: str | None = None) -> dict:
    """Parse an Epic ReceiveCommunication3 request body.

    Epic documents ReceiveCommunication3 as JSON. The XML fallback exists only
    to keep the middleware tolerant during Zoom/Epic integration testing.

    Returns:
        {
            "recipient_id":       str         # ZCC agent id, required
            "recipient_id_type":  str | None
            "patient_id":         str | None  # LookupID.ID, PatientID, or LookupInformation
            "patient_id_type":    str | None  # LookupID.Type, PatientIDType, or LookupInformationType
            "communication_type": str | None
            "caller_number":      str | None
            "dialed_number":      str | None
            "call_id":            str | None
            "lookup_type":        str | None
        }
    """
    if not raw_body:
        raise InvalidEpicRequest("INVALID-REQUEST", "empty body")

    stripped = raw_body.lstrip()
    if stripped.startswith(b"<"):
        parsed = _parse_receive_communication3_xml(raw_body)
    else:
        parsed = _parse_receive_communication3_json(raw_body, content_type)

    if not parsed.get("recipient_id"):
        raise InvalidEpicRequest("NO-USER-ID", "RecipientID is required")

    return parsed


def _parse_receive_communication3_json(raw_body: bytes, content_type: str | None) -> dict:
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

    return {
        "recipient_id": _json_text(payload.get("RecipientID")),
        "recipient_id_type": _json_text(payload.get("RecipientIDType")),
        "patient_id": patient_id,
        "patient_id_type": patient_id_type,
        "communication_type": _json_text(payload.get("CommunicationType")),
        "caller_number": _json_text(payload.get("CallerPhoneNumber")),
        "dialed_number": _json_text(payload.get("DialedPhoneNumber")),
        "call_id": _json_text(payload.get("CallID")),
        "lookup_type": _json_text(payload.get("LookupType")),
    }


def _parse_receive_communication3_xml(xml_bytes: bytes) -> dict:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.warning(f"epic.request_parser | malformed ReceiveCommunication3 XML: {e}")
        raise InvalidEpicRequest("INVALID-REQUEST", f"malformed XML: {e}")

    patient_id = (
        _xml_child_text(root, "LookupID", "ID")
        or _xml_local_text(root, "PatientID")
        or _xml_local_text(root, "LookupInformation")
    )
    patient_id_type = (
        _xml_child_text(root, "LookupID", "Type")
        or _xml_local_text(root, "PatientIDType")
        or _xml_local_text(root, "LookupInformationType")
    )

    return {
        "recipient_id": _xml_local_text(root, "RecipientID"),
        "recipient_id_type": _xml_local_text(root, "RecipientIDType"),
        "patient_id": patient_id,
        "patient_id_type": patient_id_type,
        "communication_type": _xml_local_text(root, "CommunicationType"),
        "caller_number": _xml_local_text(root, "CallerPhoneNumber"),
        "dialed_number": _xml_local_text(root, "DialedPhoneNumber"),
        "call_id": _xml_local_text(root, "CallID"),
        "lookup_type": _xml_local_text(root, "LookupType"),
    }


def _json_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _xml_local_text(root: ET.Element, local_name: str) -> str | None:
    for element in root.iter():
        if _local_name(element.tag) == local_name and element.text:
            text = element.text.strip()
            if text:
                return text
    return None


def _xml_child_text(root: ET.Element, parent_name: str, child_name: str) -> str | None:
    for element in root.iter():
        if _local_name(element.tag) != parent_name:
            continue
        for child in element:
            if _local_name(child.tag) == child_name and child.text:
                text = child.text.strip()
                if text:
                    return text
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag

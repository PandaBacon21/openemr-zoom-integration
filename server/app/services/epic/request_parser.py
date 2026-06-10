"""Parse the Epic PatientLookUp (2012) XML request body.

Epic's contract uses a SOAP-style XML document under the
`urn:Epic-com:EMPI.2012.Services.Patient` namespace. We accept the full Epic
schema but only act on the fields Zoomly's IVR-driven CTI flow actually
populates: PatientID + PatientIDType, DateOfBirth, NationalIdentifier (SSN),
phone numbers, and the required UserID identifying which ZCC agent is doing
the lookup.

Faults raised here use Epic's documented fault codes so the route can
translate them straight into the XML fault envelope without further mapping.
"""

import logging
import re
from xml.etree import ElementTree as ET

from .constants import EPIC_XML_NAMESPACE


logger = logging.getLogger(__name__)


class InvalidEpicRequest(Exception):
    """Raised when the inbound XML can't be parsed or is missing required fields.

    `fault_code` matches one of Epic's documented PatientLookUp fault codes so
    the route can return it verbatim inside the <Fault> envelope.
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

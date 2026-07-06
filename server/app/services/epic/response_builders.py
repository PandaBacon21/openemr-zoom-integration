"""Epic-shaped response builders for the ZCC CTI middleware.

Builds `<PatientLookupResult>` and `<Fault>` documents under the
`urn:Epic-com:EMPI.2012.Services.Patient` namespace. The output is a UTF-8
encoded XML byte string ready to hand to Flask's response with
`Content-Type: application/xml; charset=utf-8`.

Also builds the FHIR R4 JSON documents used by the Epic-style Practitioner
endpoint: Bundle searchsets and OperationOutcome errors.

Field coverage is intentionally partial: we emit only the elements we have
data for in OpenEMR's `patient_data`, and omit Epic-specific extensions
(CareTeam, EmploymentInformation, etc.) entirely. Zoom's CTI client should
treat absent elements as empty.

If integration testing reveals ZCC needs additional elements or different
field names, iterate here — every Epic-shaped response is built through
this module.
"""

import json
from xml.etree import ElementTree as ET

from .constants import EPIC_XML_NAMESPACE


# Microsoft Serialization Arrays namespace — Epic wraps phone/street string
# arrays in this secondary namespace per the published schema.
_MS_ARRAYS_NS = "http://schemas.microsoft.com/2003/10/Serialization/Arrays"


def _e(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    """Append a child element under the Epic namespace; only set text if non-None."""
    el = ET.SubElement(parent, f"{{{EPIC_XML_NAMESPACE}}}{tag}")
    if text is not None:
        el.text = text
    return el


def _format_name(row: dict) -> str:
    """Render `Last, First` to match Epic's <Name> formatting."""
    last = (row.get("lname") or "").strip()
    first = (row.get("fname") or "").strip()
    if last and first:
        return f"{last}, {first}"
    return last or first


def _format_dob(value) -> str | None:
    """patient_data.DOB comes back as datetime.date from MariaDB; serialize to YYYY-MM-DD."""
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _format_ssn(last4: str | None) -> str | None:
    """Epic-style masked NationalIdentifier: xxx-xx-1234."""
    if not last4 or len(last4) < 4:
        return None
    return f"xxx-xx-{last4}"


def _append_patient(parent: ET.Element, row: dict) -> None:
    """Serialize one patient_data row as <Patient> under the given parent."""
    patient = _e(parent, "Patient")

    # --- Addresses (single address per row in OpenEMR; emit if any field present) ---
    has_address = any(row.get(k) for k in ("street", "city", "state", "postal_code"))
    has_phone = any(row.get(k) for k in ("phone_cell", "phone_home"))
    if has_address or has_phone or row.get("email"):
        addresses = _e(patient, "Addresses")
        addr = _e(addresses, "Address")
        if row.get("city"):
            _e(addr, "City", row["city"])
        if row.get("state"):
            _e(addr, "State", row["state"])
        if row.get("postal_code"):
            _e(addr, "PostalCode", row["postal_code"])
        if row.get("email"):
            email_container = _e(addr, "Email")
            email_str = ET.SubElement(email_container, f"{{{_MS_ARRAYS_NS}}}string")
            email_str.text = row["email"]
        # Phones
        if has_phone:
            phones = _e(addr, "PhoneNumbers")
            for col, label in (("phone_cell", "Cell"), ("phone_home", "Home")):
                number = (row.get(col) or "").strip()
                if not number:
                    continue
                phone_info = _e(phones, "PhoneInfo")
                _e(phone_info, "Number", number)
                _e(phone_info, "Type", label)
        # Street
        if row.get("street"):
            street_container = _e(addr, "Street")
            street_str = ET.SubElement(street_container, f"{{{_MS_ARRAYS_NS}}}string")
            street_str.text = row["street"]
        _e(addr, "Type", "PERMANENT")

    # --- DateOfBirth ---
    dob = _format_dob(row.get("DOB"))
    if dob:
        _e(patient, "DateOfBirth", dob)

    # --- IDs (MRN + FHIR) ---
    ids = _e(patient, "IDs")
    if row.get("pubpid"):
        id_type = _e(ids, "IDType")
        _e(id_type, "ID", str(row["pubpid"]))
        _e(id_type, "Type", "MRN")
    if row.get("uuid_hex"):
        id_type = _e(ids, "IDType")
        _e(id_type, "ID", row["uuid_hex"])
        _e(id_type, "Type", "FHIR")
    # Also emit the internal numeric pid for our own correlation
    if row.get("pid") is not None:
        id_type = _e(ids, "IDType")
        _e(id_type, "ID", str(row["pid"]))
        _e(id_type, "Type", "INTERNAL")

    # --- Name + NameComponents ---
    name_str = _format_name(row)
    if name_str:
        _e(patient, "Name", name_str)
    components = _e(patient, "NameComponents")
    _e(components, "FirstName", (row.get("fname") or "").strip())
    _e(components, "LastName", (row.get("lname") or "").strip())
    if row.get("mname"):
        _e(components, "MiddleName", row["mname"].strip())
    if row.get("title"):
        _e(components, "Title", row["title"].strip())

    # --- NationalIdentifier (masked) ---
    masked_ssn = _format_ssn(row.get("ssn_last4"))
    if masked_ssn:
        _e(patient, "NationalIdentifier", masked_ssn)

    # --- Sex ---
    if row.get("sex"):
        _e(patient, "Sex", row["sex"])


def build_patient_lookup_response_xml(rows: list[dict]) -> bytes:
    """Build a <PatientLookupResult> envelope around the given rows.

    Returns the XML body as UTF-8 bytes including the standard
    <?xml version='1.0' encoding='utf-8'?> declaration.
    """
    root = ET.Element(f"{{{EPIC_XML_NAMESPACE}}}PatientLookupResult")
    patients = _e(root, "Patients")
    for row in rows:
        _append_patient(patients, row)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_fault_xml(code: str, message: str) -> bytes:
    """Build a <Fault> envelope with one of Epic's documented PatientLookUp fault codes."""
    root = ET.Element(f"{{{EPIC_XML_NAMESPACE}}}Fault")
    _e(root, "Code", code)
    _e(root, "Message", message)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_receive_communication_ack_json(call_id: str | None = None) -> bytes:
    """Build the JSON ReceiveCommunication3 success ack documented by Epic."""
    return _json_bytes({"EpicCallID": call_id or ""})


def build_receive_communication_fault_json(code: str, message: str) -> bytes:
    """Build a compact JSON fault for malformed ReceiveCommunication3 requests."""
    return _json_bytes({
        "ErrorCode": code,
        "Message": message,
    })


def build_practitioner_bundle_fhir(
    practitioners: list[dict],
    *,
    self_url: str,
    practitioner_base_url: str,
) -> bytes:
    """Build a FHIR R4 Practitioner searchset Bundle as UTF-8 JSON bytes."""
    entries: list[dict] = []
    bundle: dict[str, object] = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(practitioners),
        "link": [{"relation": "self", "url": self_url}],
        "entry": entries,
    }

    for practitioner in practitioners:
        resource = _practitioner_resource(practitioner)
        full_url = f"{practitioner_base_url.rstrip('/')}/{resource['id']}"
        entries.append({
            "link": [{"relation": "self", "url": full_url}],
            "fullUrl": full_url,
            "resource": resource,
            "search": {"mode": "match"},
        })

    return _json_bytes(bundle)


def build_operation_outcome_fhir(
    *,
    error_code: str,
    message: str,
    issue_code: str = "invalid",
    severity: str = "fatal",
) -> bytes:
    """Build a FHIR R4 OperationOutcome response body."""
    return _json_bytes({
        "resourceType": "OperationOutcome",
        "issue": [{
            "severity": severity,
            "code": issue_code,
            "details": {
                "coding": [{
                    "system": "urn:epic:error-code",
                    "code": error_code,
                }],
                "text": message,
            },
            "diagnostics": message,
        }],
    })


def _practitioner_resource(practitioner: dict) -> dict:
    given = [
        value for value in (
            practitioner.get("first_name"),
            practitioner.get("middle_name"),
        )
        if value
    ]
    family = practitioner.get("last_name") or ""
    physician_type = practitioner.get("physician_type") or ""

    name: dict[str, object] = {
        "use": "usual",
        "text": _practitioner_name_text(practitioner),
        "family": family,
        "given": given,
    }
    resource: dict[str, object] = {
        "resourceType": "Practitioner",
        "id": practitioner.get("fhir_id") or f"openemr-user-{practitioner['openemr_user_id']}",
        "identifier": _practitioner_identifiers(practitioner),
        "active": bool(practitioner.get("active")),
        "name": [name],
    }

    title = practitioner.get("title")
    if title:
        name["prefix"] = [title]

    if physician_type:
        name["suffix"] = [physician_type]
        resource["qualification"] = [{
            "code": {
                "text": physician_type,
            },
        }]

    email = practitioner.get("email")
    if email:
        resource["telecom"] = [{
            "system": "email",
            "value": email,
        }]

    return resource


def _practitioner_identifiers(practitioner: dict) -> list[dict]:
    identifiers: list[dict] = []

    npi = practitioner.get("npi")
    if npi:
        identifiers.append({
            "use": "usual",
            "type": {"text": "NPI"},
            "system": "http://hl7.org/fhir/sid/us-npi",
            "value": npi,
        })

    # Tax ID (EIN). Epic returns TIN with identifier type text "TIN" under
    # OID 2.16.840.1.113883.4.4 (no dedicated system URL), starting Nov 2024.
    tin = practitioner.get("tin")
    if tin:
        identifiers.append({
            "use": "usual",
            "type": {"text": "TIN"},
            "system": "urn:oid:2.16.840.1.113883.4.4",
            "value": tin,
        })

    openemr_user_id = practitioner.get("openemr_user_id")
    if openemr_user_id is not None:
        identifiers.append({
            "use": "usual",
            "type": {"text": "INTERNAL"},
            "system": "urn:zoomly:openemr:user",
            "value": str(openemr_user_id),
        })

    return identifiers


def _practitioner_name_text(practitioner: dict) -> str:
    given = " ".join(
        value for value in (
            practitioner.get("first_name"),
            practitioner.get("middle_name"),
        )
        if value
    )
    family = practitioner.get("last_name") or ""
    physician_type = practitioner.get("physician_type") or ""

    name = " ".join(value for value in (given, family) if value).strip()
    if physician_type:
        return f"{name}, {physician_type}" if name else physician_type
    return name


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

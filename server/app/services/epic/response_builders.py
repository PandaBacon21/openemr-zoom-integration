"""Epic-shaped XML response builders for the ZCC CTI middleware.

Builds `<PatientLookupResult>` and `<Fault>` documents under the
`urn:Epic-com:EMPI.2012.Services.Patient` namespace. The output is a UTF-8
encoded XML byte string ready to hand to Flask's response with
`Content-Type: application/xml; charset=utf-8`.

Field coverage is intentionally partial: we emit only the elements we have
data for in OpenEMR's `patient_data`, and omit Epic-specific extensions
(CareTeam, EmploymentInformation, etc.) entirely. Zoom's CTI client should
treat absent elements as empty.

If integration testing reveals ZCC needs additional elements or different
field names, iterate here — every response is built through these two
functions.
"""

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

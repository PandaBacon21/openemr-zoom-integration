"""Patient lookup against OpenEMR's MariaDB for the Epic-ZCC CTI flow.

Search is OR across the supplied criteria — phone, DOB, MRN/FHIR ID, and
SSN last-4 — so a single phone number shared by a mom and her kid returns
both rows for ZCC to disambiguate. All inputs are bound parameters so
callers can pass user-controlled values directly without escaping.

We don't impose a confidence order or pick a "best" match: which criteria
to query on (and in what order) is Zoom's call, and ReceiveCommunication3
will later tell us which specific patient was chosen. We just return all
matching rows along with which of the criteria each row hit.
"""

import logging
import re

from sqlalchemy import text

from app.extensions import get_openemr_db_engine


logger = logging.getLogger(__name__)


def _phone_digits(raw: str) -> str:
    """Strip every non-digit so the digits-only comparison ignores formatting."""
    return re.sub(r"\D", "", raw)


def search_patients(criteria: dict) -> tuple[list[dict], list[str]]:
    """Search OpenEMR `patient_data` for rows matching any supplied criterion.

    `criteria` accepts:
        patient_id      (str)        — MRN / EPI / FHIR (paired with patient_id_type)
        patient_id_type (str | None) — 'EPI' | 'MRN' | 'FHIR' (case-insensitive);
                                       missing or unknown values default to MRN
        dob             (str)        — ISO YYYY-MM-DD
        ssn_last4       (str)        — 4-digit string, already normalized
        phones          (list[str])  — raw phone strings; we strip non-digits

    Returns (rows, queried_fields):
        rows           — list of dicts, one per matched patient_data row;
                         each row carries `_matched_on` listing which of the
                         queried criteria hit that specific row
        queried_fields — the criterion keys we actually issued SQL for (for
                         audit only — not a confidence ranking)

    Empty result is a normal outcome (no exception). DB errors propagate.
    """
    where_clauses: list[str] = []
    params: dict[str, object] = {}
    queried_fields: list[str] = []

    patient_id = criteria.get("patient_id")
    patient_id_type = (criteria.get("patient_id_type") or "MRN").upper()
    if patient_id:
        if patient_id_type == "FHIR":
            where_clauses.append("LOWER(HEX(uuid)) = LOWER(:patient_id)")
            params["patient_id"] = patient_id
            queried_fields.append("fhir")
        else:
            # EPI / MRN / unknown — treat as MRN (pubpid).
            where_clauses.append("pubpid = :patient_id")
            params["patient_id"] = patient_id
            queried_fields.append("mrn")

    dob = criteria.get("dob")
    if dob:
        where_clauses.append("DATE(DOB) = :dob")
        params["dob"] = dob
        queried_fields.append("dob")

    ssn_last4 = criteria.get("ssn_last4")
    if ssn_last4:
        where_clauses.append("RIGHT(ss, 4) = :ssn_last4")
        params["ssn_last4"] = ssn_last4
        queried_fields.append("ssn_last4")

    phones = criteria.get("phones") or []
    phone_clauses: list[str] = []
    for idx, phone in enumerate(phones):
        digits = _phone_digits(phone)
        if not digits:
            continue
        key_cell = f"phone_cell_{idx}"
        key_home = f"phone_home_{idx}"
        # Compare digits-only on both columns so '(303) 555-0101' stored
        # in any format matches an inbound '3035550101'.
        phone_clauses.append(
            f"REGEXP_REPLACE(phone_cell, '[^0-9]', '') = :{key_cell} "
            f"OR REGEXP_REPLACE(phone_home, '[^0-9]', '') = :{key_home}"
        )
        params[key_cell] = digits
        params[key_home] = digits
    if phone_clauses:
        where_clauses.append("(" + " OR ".join(phone_clauses) + ")")
        queried_fields.append("phone")

    if not where_clauses:
        return [], []

    sql = text(f"""
        SELECT pid, pubpid, LOWER(HEX(uuid)) AS uuid_hex,
               fname, mname, lname, title,
               DOB, sex,
               street, city, state, postal_code,
               phone_cell, phone_home, email,
               RIGHT(ss, 4) AS ssn_last4
        FROM patient_data
        WHERE {" OR ".join(where_clauses)}
        LIMIT 50
    """)

    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        result = conn.execute(sql, params)
        rows = [dict(row._mapping) for row in result]

    for row in rows:
        row["_matched_on"] = _row_matched_fields(row, criteria)

    return rows, queried_fields


def _row_matched_fields(row: dict, criteria: dict) -> list[str]:
    """Return the criterion keys that matched this specific row.

    Order follows the criteria dict's insertion order — i.e. the order Zoom
    sent them. We don't rerank.
    """
    matched: list[str] = []

    patient_id = criteria.get("patient_id")
    patient_id_type = (criteria.get("patient_id_type") or "MRN").upper()
    if patient_id:
        if patient_id_type == "FHIR" and (row.get("uuid_hex") or "").lower() == patient_id.lower():
            matched.append("fhir")
        elif patient_id_type != "FHIR" and row.get("pubpid") == patient_id:
            matched.append("mrn")

    dob = criteria.get("dob")
    if dob:
        row_dob = row.get("DOB")
        row_dob_str = row_dob.isoformat() if (row_dob and hasattr(row_dob, "isoformat")) else str(row_dob)
        if row_dob_str == dob:
            matched.append("dob")

    ssn_last4 = criteria.get("ssn_last4")
    if ssn_last4 and row.get("ssn_last4") == ssn_last4:
        matched.append("ssn_last4")

    phones = criteria.get("phones") or []
    digits_set = {_phone_digits(p) for p in phones if _phone_digits(p)}
    if digits_set:
        cell = _phone_digits(row.get("phone_cell") or "")
        home = _phone_digits(row.get("phone_home") or "")
        if cell in digits_set or home in digits_set:
            matched.append("phone")

    return matched

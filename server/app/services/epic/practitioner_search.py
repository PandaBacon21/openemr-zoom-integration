"""Practitioner search against OpenEMR's MariaDB for the Epic-ZCC CTI flow.

Epic's Practitioner.Search R4 endpoint supports a few minimum search shapes:
identifier, FHIR `_id`, free-text `name`, or `family` with optional `given`.
Identifier takes priority and all other demographic/address filters are
ignored when it is present, matching Epic's published behavior.
"""

import re

from sqlalchemy import text

from app.extensions import get_openemr_db_engine


DEFAULT_PRACTITIONER_SEARCH_LIMIT = 50
MAX_PRACTITIONER_SEARCH_LIMIT = 100

_NPI_SYSTEM_MARKERS = ("us-npi", "737384")
# Epic returns/searches Tax ID (EIN) under OID 2.16.840.1.113883.4.4 with
# identifier type text "TIN". We also accept the friendlier tax/tin/ein tokens.
_TIN_SYSTEM_MARKERS = ("tax", "tin", "ein", "2.16.840.1.113883.4.4")
_FHIR_ID_TYPES = {"FHIR", "FHIRID", "FHIR ID"}


def _digits_only(value: str) -> str:
    """Strip every non-digit — used for Tax ID (EIN) comparison.

    TINs are 9 digits and never carry a country code, so a plain digit strip
    is correct here.
    """
    return re.sub(r"\D", "", value or "")


def search_practitioners(criteria: dict) -> list[dict]:
    """Search active OpenEMR provider users for Epic FHIR Practitioner.Search.

    Supported criteria keys (all Epic Practitioner.Search spec parameters —
    phone is intentionally not a search key; Epic has no phone search param):
        search_type         — 'identifier' | '_id' | 'name' | 'family'
        identifier          — token value after any `system|` prefix; the
                              system selects NPI, Tax ID (EIN), FHIR UUID, or
                              internal user id (systemless/unknown matches any)
        identifier_system   — optional token system/type prefix
        fhir_id             — Practitioner FHIR id / OpenEMR users.uuid hex
        name                — free-text name fragment
        family              — last-name fragment
        given               — optional first/middle-name fragment
        count               — result limit, already parsed and bounded by caller

    Each result carries the provider's stored phone numbers (phone/cell/work)
    so the caller (the practitioner route) can key the screen-pop cache by the
    provider's own ANI — the number ReceiveCommunication3 echoes back.

    Empty result is a normal outcome. DB errors propagate so routes can audit
    and emit FHIR OperationOutcome diagnostics.
    """
    where_clauses = [
        "u.active = 1",
        "u.authorized = 1",
        "u.abook_type = 'physician'",
        "u.npi IS NOT NULL",
        "TRIM(u.npi) != ''",
    ]
    params: dict[str, object] = {}

    search_type = criteria["search_type"]
    if search_type == "identifier":
        identifier_clause, identifier_params = _identifier_clause(
            criteria["identifier"],
            criteria.get("identifier_system"),
        )
        where_clauses.append(f"({identifier_clause})")
        params.update(identifier_params)
    elif search_type == "_id":
        where_clauses.append(
            "(LOWER(HEX(u.uuid)) = LOWER(:fhir_id) OR CAST(u.id AS CHAR) = :fhir_id)"
        )
        params["fhir_id"] = criteria["fhir_id"]
    elif search_type == "name":
        where_clauses.append(
            "("
            "LOWER(CONCAT_WS(' ', u.fname, u.mname, u.lname)) LIKE :name "
            "OR LOWER(CONCAT_WS(' ', u.lname, u.fname, u.mname)) LIKE :name"
            ")"
        )
        params["name"] = _like(criteria["name"])
    elif search_type == "family":
        where_clauses.append("LOWER(u.lname) LIKE :family")
        params["family"] = _like(criteria["family"])
        if criteria.get("given"):
            where_clauses.append(
                "(LOWER(u.fname) LIKE :given OR LOWER(u.mname) LIKE :given)"
            )
            params["given"] = _like(criteria["given"])
    else:
        raise ValueError(f"unsupported practitioner search_type={search_type!r}")

    limit = int(criteria.get("count") or DEFAULT_PRACTITIONER_SEARCH_LIMIT)
    limit = max(1, min(limit, MAX_PRACTITIONER_SEARCH_LIMIT))

    sql = text(f"""
        SELECT u.id AS openemr_user_id,
               LOWER(HEX(u.uuid)) AS fhir_id,
               u.fname,
               u.mname,
               u.lname,
               u.title,
               u.email,
               u.npi,
               u.federaltaxid,
               u.phone,
               u.phonecell,
               u.phonew1,
               u.phonew2,
               u.active,
               u.facility_id,
               f.name AS facility_name,
               u.physician_type,
               u.specialty
        FROM users u
        LEFT JOIN facility f ON f.id = u.facility_id
        WHERE {" AND ".join(where_clauses)}
        ORDER BY u.lname, u.fname, u.id
        LIMIT {limit}
    """)

    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        result = conn.execute(sql, params)
        return [_normalize_row(dict(row._mapping)) for row in result]


def _identifier_clause(identifier: str, system: str | None) -> tuple[str, dict[str, object]]:
    """Build the WHERE fragment for a FHIR token identifier search.

    Epic supports both `identifier=value` and `identifier=system|value`.
    For NPI systems we search only NPI. For FHIR systems we search the
    OpenEMR UUID hex. For unknown/custom systems we search across the
    identifiers we expose in the Bundle so ZCC can use customer-specific ID
    types during setup without needing another code path.
    """
    params: dict[str, object] = {
        "identifier_value": identifier,
        "tin_digits": _digits_only(identifier),
    }
    # Broad match used when no system is given or the system is unrecognized:
    # NPI, internal user id, FHIR UUID, or Tax ID (EIN, digits-compared). The
    # `:tin_digits != ''` guard keeps a non-numeric identifier from matching a
    # NULL/blank federaltaxid, and NPI (10 digits) never collides with a TIN
    # (9 digits) so including both here is safe.
    any_id_clause = (
        "u.npi = :identifier_value "
        "OR CAST(u.id AS CHAR) = :identifier_value "
        "OR LOWER(HEX(u.uuid)) = LOWER(:identifier_value) "
        "OR (:tin_digits != '' AND REGEXP_REPLACE(u.federaltaxid, '[^0-9]', '') = :tin_digits)"
    )
    if not system:
        return any_id_clause, params

    system_clean = system.strip()
    system_lower = system_clean.lower()
    system_upper = system_clean.upper()

    if system_upper in {"NPI", "NPIID"} or any(
        marker in system_lower for marker in _NPI_SYSTEM_MARKERS
    ):
        return "u.npi = :identifier_value", params
    if system_upper in {"TAX", "TIN", "EIN"} or any(
        marker in system_lower for marker in _TIN_SYSTEM_MARKERS
    ):
        return "REGEXP_REPLACE(u.federaltaxid, '[^0-9]', '') = :tin_digits", params
    if system_upper in _FHIR_ID_TYPES or "fhir" in system_lower:
        return "LOWER(HEX(u.uuid)) = LOWER(:identifier_value)", params
    if system_upper in {"INTERNAL", "USER", "USERID", "OPENEMR"}:
        return "CAST(u.id AS CHAR) = :identifier_value", params

    return any_id_clause, params


def _like(value: str) -> str:
    return f"%{value.strip().lower()}%"


def _normalize_row(row: dict) -> dict:
    fhir_id = (row.get("fhir_id") or "").lower()
    openemr_user_id = row.get("openemr_user_id")
    if not fhir_id and openemr_user_id is not None:
        fhir_id = f"openemr-user-{openemr_user_id}"

    return {
        "fhir_id": fhir_id,
        "openemr_user_id": openemr_user_id,
        "active": bool(row.get("active")),
        "first_name": (row.get("fname") or "").strip(),
        "middle_name": (row.get("mname") or "").strip(),
        "last_name": (row.get("lname") or "").strip(),
        "title": (row.get("title") or "").strip(),
        "email": (row.get("email") or "").strip(),
        "npi": (row.get("npi") or "").strip(),
        "tin": (row.get("federaltaxid") or "").strip(),
        "phone": (row.get("phone") or "").strip(),
        "phone_cell": (row.get("phonecell") or "").strip(),
        "phone_work": (row.get("phonew1") or "").strip(),
        "phone_work2": (row.get("phonew2") or "").strip(),
        "facility_id": row.get("facility_id") or None,
        "facility_name": row.get("facility_name") or None,
        "physician_type": (row.get("physician_type") or "").strip(),
        "specialty": (row.get("specialty") or "").strip(),
    }

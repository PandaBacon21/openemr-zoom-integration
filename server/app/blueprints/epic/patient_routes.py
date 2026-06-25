"""Epic PatientLookUp (2012) endpoint for the ZCC CTI middleware.

ZCC POSTs a JSON PatientLookUp request after the IVR has collected one or
more search criteria (phone, DOB, MRN/FHIR ID, SSN last-4). We OR-search
OpenEMR's patient_data and return all matches in Epic's PatientLookupResult
XML envelope. The result is cached keyed by normalized caller phone so the
subsequent ReceiveCommunication3 can drive the screen pop without re-querying
OpenEMR.

UserID/UserIDType in the request are per-account Epic background service
credentials configured in ZCC — not the individual agent handling the call.
"""

import logging
from flask import Response, g, request

from app.blueprints.auth.auth_helpers import verify_bearer_token_in_store
from app.blueprints.epic import epic_bp
from app.services.audit import write_audit_log
from app.services.epic.lookup_cache import cache_lookup
from app.services.epic.patient_search import _phone_digits, search_patients
from app.services.epic.request_parser import InvalidEpicRequest, parse_patient_lookup_request
from app.services.epic.response_builders import build_fault_xml, build_patient_lookup_response_xml


logger = logging.getLogger(__name__)


_XML_CONTENT_TYPE = "application/xml; charset=utf-8"


def _xml_response(body: bytes, status: int = 200) -> Response:
    return Response(body, status=status, mimetype=_XML_CONTENT_TYPE)


def _fault_response(code: str, message: str, *, account_id: str | None, reason: str) -> Response:
    write_audit_log(
        event_type="epic_zcc.patient_lookup_failed",
        success=False,
        zoom_account_id=account_id,
        detail={"reason": reason, "fault_code": code},
        error_message=message,
    )
    return _xml_response(build_fault_xml(code, message), status=400)


@epic_bp.route(
    "/api/epic/2012/EMPI/Patient/PATIENTLOOKUP/Lookup",
    methods=["POST"],
)
def patient_lookup(zoom_account_id: str):
    # Flask passes zoom_account_id from the blueprint URL prefix; before_request
    # already resolved it onto g.zoom_account and the bearer guard checks it.
    _ = zoom_account_id
    # below double-checks the token also belongs to this account.
    bearer_failure = verify_bearer_token_in_store()
    if bearer_failure is not None:
        return bearer_failure

    account = g.zoom_account

    raw_body = request.get_data()
    if not raw_body:
        return _fault_response("INVALID-REQUEST", "empty body",
                               account_id=account.account_id, reason="empty_body")

    logger.info(
        "epic.patient_lookup | raw_body account_id=%s\n%s",
        account.account_id,
        raw_body.decode("utf-8", errors="replace"),
    )

    try:
        criteria = parse_patient_lookup_request(raw_body)
    except InvalidEpicRequest as e:
        reason = {
            "INVALID-USER": "missing_user",
            "INSUFFICIENT-CRITERIA": "insufficient_criteria",
            "INVALID-REQUEST": "malformed_xml",
        }.get(e.fault_code, "malformed_xml")
        return _fault_response(e.fault_code, e.message,
                               account_id=account.account_id, reason=reason)

    queried_fields_from_criteria = [
        k for k, v in (
            ("patient_id", criteria.get("patient_id")),
            ("dob", criteria.get("dob")),
            ("ssn_last4", criteria.get("ssn_last4")),
            ("phones", criteria.get("phones")),
        )
        if v
    ]
    logger.info(
        "epic.patient_lookup | parsed criteria "
        f"account_id={account.account_id} "
        f"user_id={criteria['user_id']!r} "
        f"user_id_type={criteria.get('user_id_type')!r} "
        f"patient_id={criteria.get('patient_id')!r} "
        f"patient_id_type={criteria.get('patient_id_type')!r} "
        f"dob={criteria.get('dob')!r} "
        f"ssn_last4={criteria.get('ssn_last4')!r} "
        f"phones={criteria.get('phones')!r}"
    )
    write_audit_log(
        event_type="epic_zcc.patient_lookup_received",
        success=True,
        zoom_account_id=account.account_id,
        detail={
            "criteria_fields": queried_fields_from_criteria,
            "patient_id_type": criteria.get("patient_id_type"),
            "epic_service_user": criteria["user_id"],
        },
    )

    try:
        rows, queried_fields = search_patients(criteria)
    except Exception as e:
        logger.error(f"epic.patient_lookup | DB error: {e}", exc_info=True)
        return _fault_response("INVALID-REQUEST", "search failed",
                               account_id=account.account_id, reason="db_error")

    phones = criteria.get("phones") or []
    if phones and (cache_phone := _phone_digits(phones[0])):
        cache_lookup(account.account_id, cache_phone, rows, queried_fields)

    write_audit_log(
        event_type="epic_zcc.patient_lookup_resolved",
        success=True,
        zoom_account_id=account.account_id,
        detail={
            "match_count": len(rows),
            "queried_fields": queried_fields,
            "epic_service_user": criteria["user_id"],
        },
    )

    return _xml_response(build_patient_lookup_response_xml(rows), status=200)

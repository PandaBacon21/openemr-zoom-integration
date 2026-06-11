"""Epic ReceiveCommunication3 endpoint for ZCC CTI screen-pop routing."""

import logging

from flask import Response, g, request

from app.blueprints.auth.auth_helpers import verify_bearer_token_in_store
from app.blueprints.epic import epic_bp
from app.services.audit import write_audit_log
from app.services.epic.communication import process_receive_communication
from app.services.epic.request_parser import (
    InvalidEpicRequest,
    parse_receive_communication3_request,
)
from app.services.epic.response_builders import (
    build_receive_communication_ack_json,
    build_receive_communication_ack_xml,
    build_receive_communication_fault_json,
    build_receive_communication_fault_xml,
)


logger = logging.getLogger(__name__)

_JSON_CONTENT_TYPE = "application/json; charset=utf-8"
_XML_CONTENT_TYPE = "application/xml; charset=utf-8"


@epic_bp.route(
    "/api/epic/2023/Common/Utility/RECEIVECOMMUNICATION3/ReceiveCommunication3",
    methods=["POST"],
)
def receive_communication3(zoom_account_id: str):
    # Flask passes zoom_account_id from the blueprint URL prefix; before_request
    # already resolved it onto g.zoom_account and the bearer guard checks it.
    _ = zoom_account_id
    bearer_failure = verify_bearer_token_in_store()
    if bearer_failure is not None:
        return bearer_failure

    account = g.zoom_account
    raw_body = request.get_data()
    wants_xml = raw_body.lstrip().startswith(b"<")

    try:
        payload = parse_receive_communication3_request(
            raw_body,
            request.headers.get("Content-Type"),
        )
    except InvalidEpicRequest as e:
        reason = {
            "NO-USER-ID": "missing_recipient",
            "INVALID-REQUEST": "malformed_body",
        }.get(e.fault_code, "invalid_request")
        write_audit_log(
            event_type="epic_zcc.receive_communication_failed",
            success=False,
            zoom_account_id=account.account_id,
            detail={"reason": reason, "fault_code": e.fault_code},
            error_message=e.message,
        )
        return _fault_response(e.fault_code, e.message, wants_xml=wants_xml)

    write_audit_log(
        event_type="epic_zcc.receive_communication_received",
        success=True,
        zoom_account_id=account.account_id,
        detail={
            "recipient_id": payload["recipient_id"],
            "patient_id_type": payload.get("patient_id_type"),
            "has_patient_id": bool(payload.get("patient_id")),
            "communication_type": payload.get("communication_type"),
            "call_id": payload.get("call_id"),
        },
    )

    try:
        process_receive_communication(account, payload)
    except Exception as e:
        logger.error(
            "epic.receive_communication | unexpected handler error "
            f"account_id={account.account_id}: {e}",
            exc_info=True,
        )
        write_audit_log(
            event_type="epic_zcc.receive_communication_failed",
            success=False,
            zoom_account_id=account.account_id,
            detail={
                "reason": "handler_error",
                "recipient_id": payload["recipient_id"],
            },
            error_message=str(e),
        )

    return _ack_response(payload.get("call_id"), wants_xml=wants_xml)


def _ack_response(call_id: str | None, *, wants_xml: bool) -> Response:
    if wants_xml:
        return Response(
            build_receive_communication_ack_xml(call_id),
            status=200,
            content_type=_XML_CONTENT_TYPE,
        )
    return Response(
        build_receive_communication_ack_json(call_id),
        status=200,
        content_type=_JSON_CONTENT_TYPE,
    )


def _fault_response(code: str, message: str, *, wants_xml: bool) -> Response:
    if wants_xml:
        return Response(
            build_receive_communication_fault_xml(code, message),
            status=400,
            content_type=_XML_CONTENT_TYPE,
        )
    return Response(
        build_receive_communication_fault_json(code, message),
        status=400,
        content_type=_JSON_CONTENT_TYPE,
    )

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
    build_receive_communication_fault_json,
)


logger = logging.getLogger(__name__)

_JSON_CONTENT_TYPE = "application/json; charset=utf-8"


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

    logger.info(
        "epic.receive_communication3 | raw_body account_id=%s\n%s",
        account.account_id,
        raw_body.decode("utf-8", errors="replace"),
    )

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
        return Response(
            build_receive_communication_fault_json(e.fault_code, e.message),
            status=400,
            content_type=_JSON_CONTENT_TYPE,
        )

    logger.info(
        "epic.receive_communication | parsed payload "
        f"account_id={account.account_id} "
        f"recipient_id={payload['recipient_id']!r} "
        f"recipient_id_type={payload.get('recipient_id_type')!r} "
        f"patient_id={payload.get('patient_id')!r} "
        f"patient_id_type={payload.get('patient_id_type')!r} "
        f"communication_type={payload.get('communication_type')!r} "
        f"caller_number={payload.get('caller_number')!r} "
        f"dialed_number={payload.get('dialed_number')!r} "
        f"call_id={payload.get('call_id')!r} "
        f"lookup_type={payload.get('lookup_type')!r}"
    )
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

    return Response(
        build_receive_communication_ack_json(payload.get("call_id")),
        status=200,
        content_type=_JSON_CONTENT_TYPE,
    )

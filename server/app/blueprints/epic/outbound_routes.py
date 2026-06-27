"""OpenEMR-facing outbound CTI routes for Epic-ZCC initiate-call."""

import json
import logging
import uuid

from flask import Response, current_app, g, jsonify, request

from app.blueprints.epic import epic_bp
from app.models import UserMapping
from app.services.audit import write_audit_log
from app.services.epic.lookup_cache import cache_lookup
from app.services.epic.outbound_zcc import (
    OutboundZccError,
    OutboundZccUpstreamError,
    initiate_call,
)
from app.services.epic.patient_search import _phone_digits, get_patient_by_pid
from app.services.epic.screenpop_auth import verify_bridge_signature


logger = logging.getLogger(__name__)


@epic_bp.route("/cti/initiate-call", methods=["POST"])
def cti_initiate_call(zoom_account_id: str):
    # before_request already resolved zoom_account_id onto g.zoom_account.
    _ = zoom_account_id
    account = g.zoom_account
    raw_body = request.get_data()

    signature_failure = _verify_openemr_hmac(account.account_id, raw_body)
    if signature_failure is not None:
        return signature_failure

    try:
        payload = json.loads(raw_body.strip() or b"{}")
    except json.JSONDecodeError as e:
        return _fail(
            account.account_id,
            "malformed_body",
            status=400,
            error_message=str(e),
        )

    phone = str(payload.get("phone") or "").strip()
    openemr_user_id = str(payload.get("openemr_user_id") or "").strip()
    openemr_patient_id = _optional_str(payload.get("openemr_patient_id"))
    if not phone:
        return _fail(account.account_id, "missing_phone", status=400)
    if not openemr_user_id:
        return _fail(account.account_id, "missing_openemr_user", status=400)

    logger.info(
        "epic.initiate_call | received "
        f"account_id={account.account_id} "
        f"phone={phone!r} "
        f"openemr_user_id={openemr_user_id!r} "
        f"openemr_patient_id={openemr_patient_id!r}"
    )

    try:
        mapping = UserMapping.query.filter_by(
            zoom_account_id=account.account_id,
            openemr_user_id=openemr_user_id,
            is_zcc_agent=True,
            is_active=True,
        ).first()
    except Exception as e:
        logger.error(
            "epic.outbound_routes | mapping lookup failed "
            f"account_id={account.account_id} openemr_user_id={openemr_user_id}: {e}",
            exc_info=True,
        )
        return _fail(
            account.account_id,
            "db_error",
            status=500,
            openemr_user_id=openemr_user_id,
            openemr_patient_id=openemr_patient_id,
            error_message=str(e),
        )

    if not mapping:
        return _fail(
            account.account_id,
            "unknown_agent",
            status=403,
            openemr_user_id=openemr_user_id,
            openemr_patient_id=openemr_patient_id,
        )
    if not mapping.zcc_user_id:
        return _fail(
            account.account_id,
            "mapping_missing_zcc_user",
            status=403,
            openemr_user_id=openemr_user_id,
            openemr_patient_id=openemr_patient_id,
        )

    epic_call_id = str(uuid.uuid4())
    try:
        result = initiate_call(
            account,
            phone,
            mapping.zcc_user_id,
            epic_call_id,
        )
    except OutboundZccUpstreamError as e:
        return _fail(
            account.account_id,
            e.reason,
            status=502,
            openemr_user_id=openemr_user_id,
            openemr_patient_id=openemr_patient_id,
            detail={"status_code": e.status_code, "body_snippet": e.body_snippet},
            error_message=e.message,
        )
    except OutboundZccError as e:
        status = 502 if e.reason == "request_failed" else 400
        return _fail(
            account.account_id,
            e.reason,
            status=status,
            openemr_user_id=openemr_user_id,
            openemr_patient_id=openemr_patient_id,
            error_message=e.message,
        )
    except Exception as e:
        logger.error(
            "epic.outbound_routes | initiate-call handler error "
            f"account_id={account.account_id}: {e}",
            exc_info=True,
        )
        return _fail(
            account.account_id,
            "handler_error",
            status=500,
            openemr_user_id=openemr_user_id,
            openemr_patient_id=openemr_patient_id,
            error_message=str(e),
        )

    write_audit_log(
        event_type="epic_zcc.click_to_dial_initiated",
        success=True,
        zoom_account_id=account.account_id,
        openemr_user_id=openemr_user_id,
        openemr_patient_id=openemr_patient_id,
        detail={
            "agent_id": mapping.zcc_user_id,
            "zcc_status_code": result.status_code,
            "epic_call_id": epic_call_id,
            "phone_system_call_id": result.phone_system_call_id,
            "has_patient_context": bool(openemr_patient_id),
        },
    )

    # Pre-load the lookup cache with the known patient so ReceiveCommunication3
    # can navigate directly without phone-based disambiguation — even if other
    # patients share the same number.
    if openemr_patient_id:
        try:
            patient_row = get_patient_by_pid(openemr_patient_id)
            if patient_row:
                cache_phone = _phone_digits(phone)
                if cache_phone:
                    patient_row["_matched_on"] = ["outbound_context"]
                    cache_lookup(account.account_id, cache_phone, [patient_row], ["outbound_context"])
                    logger.info(
                        "epic.initiate_call | cache pre-loaded "
                        f"account_id={account.account_id} "
                        f"raw_phone={phone!r} "
                        f"cache_key={cache_phone!r} "
                        f"pid={patient_row.get('pid')!r} "
                        f"name='{patient_row.get('fname')} {patient_row.get('lname')}'"
                    )
                else:
                    logger.warning(
                        "epic.initiate_call | cache pre-load skipped — phone did not normalize "
                        f"account_id={account.account_id} "
                        f"raw_phone={phone!r} "
                        f"openemr_patient_id={openemr_patient_id!r}"
                    )
        except Exception as e:
            logger.warning(
                "epic.outbound_routes | patient cache pre-load failed "
                f"account_id={account.account_id} patient_id={openemr_patient_id}: {e}"
            )

    return jsonify({"status": "ok", "zcc_status_code": result.status_code}), 200


def _verify_openemr_hmac(account_id: str, raw_body: bytes) -> Response | None:
    secret = current_app.config.get("OPENEMR_FLASK_SECRET")
    if not secret:
        logger.error("epic.cti_initiate_call | OPENEMR_FLASK_SECRET not configured")
        return _fail(account_id, "missing_secret", status=500, error_message="missing secret")

    received_signature = request.headers.get("X-Zoomly-Signature", "")
    if not received_signature:
        return _fail(account_id, "missing_signature", status=401)
    if not verify_bridge_signature(raw_body, received_signature, secret):
        return _fail(account_id, "invalid_signature", status=401)
    return None


def _optional_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _fail(
    account_id: str,
    reason: str,
    *,
    status: int,
    openemr_user_id: str | None = None,
    openemr_patient_id: str | None = None,
    detail: dict | None = None,
    error_message: str | None = None,
) -> Response:
    audit_detail = {"reason": reason}
    if detail:
        audit_detail.update(detail)
    write_audit_log(
        event_type="epic_zcc.click_to_dial_failed",
        success=False,
        zoom_account_id=account_id,
        openemr_user_id=openemr_user_id,
        openemr_patient_id=openemr_patient_id,
        detail=audit_detail,
        error_message=error_message or reason,
    )
    return Response(
        json.dumps({"error": reason}).encode("utf-8"),
        status=status,
        content_type="application/json; charset=utf-8",
    )

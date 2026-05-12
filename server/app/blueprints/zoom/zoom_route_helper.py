import logging
import hmac
import hashlib
from functools import wraps
from flask import jsonify, request, current_app
from app.services.audit import write_audit_log

logger = logging.getLogger(__name__)


def verify_openemr_signature(f):
    """
    Decorator that verifies X-Zoomly-Signature on requests originating
    from OpenEMR PHP proxies (e.g. fetch_zoom_note.php).

    Matches the signing pattern in AppointmentListener.php —
    HMAC-SHA256 over the raw request body using OPENEMR_FLASK_SECRET.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        received_sig = request.headers.get("X-Zoomly-Signature", "")
        if not received_sig:
            return jsonify({"error": "Missing signature"}), 401

        secret = current_app.config.get("OPENEMR_FLASK_SECRET", "")
        if not secret:
            logger.error("zoom | OPENEMR_FLASK_SECRET not configured")
            return jsonify({"error": "Server misconfiguration"}), 500

        expected = hmac.new(
            secret.encode("utf-8"),
            request.data.strip(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, received_sig):
            logger.warning(
                "zoom | Signature verification from OpenEMR failed — possible spoofed request"
            )
            return jsonify({"error": "Invalid signature"}), 401

        return f(*args, **kwargs)
    return decorated


def _audit_manual_fetch_failed(
    reason: str,
    error_message: str,
    *,
    encounter_number: int,
    zoom_account_id: str | None = None,
    openemr_appointment_id: str | None = None,
    openemr_provider_id: str | None = None,
    openemr_patient_id: str | None = None,
    zoom_meeting_id: str | None = None,
    zoom_note_id: str | None = None,
) -> None:
    """
    Audit a pre-API failure during manual note fetch.

    Centralizes the audit-row shape for every guard-clause in
    fetch_zoom_note so the route function stays readable.
    """
    write_audit_log(
        event_type="note.manual_fetch_failed",
        success=False,
        zoom_account_id=zoom_account_id,
        openemr_appointment_id=openemr_appointment_id,
        openemr_encounter_number=str(encounter_number),
        openemr_provider_id=openemr_provider_id,
        openemr_patient_id=openemr_patient_id,
        zoom_meeting_id=zoom_meeting_id,
        zoom_note_id=zoom_note_id,
        error_message=error_message,
        detail={"reason": reason},
    )
import logging
import hmac
import hashlib
from functools import wraps
from datetime import datetime, timezone
from sqlalchemy import text
from flask import Blueprint, jsonify, request, current_app
from app.auth.api_key import protect_with_api_key
from app.models import ZoomAccount, MeetingRecord
from app.extensions import db, get_openemr_db_engine
from app.services.audit import write_audit_log
from app.services.zoom import get_zoom_users, get_zoom_clinical_note, mark_zoom_note_completed
from app.services.openemr.openemr import write_note_to_encounter, get_provider_username

 
logger = logging.getLogger(__name__)

zoom_bp = Blueprint("zoom", __name__, url_prefix="/zoom")

@zoom_bp.before_request
def protect():
    if request.endpoint == "zoom.fetch_zoom_note":
        return
    return protect_with_api_key()


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


@zoom_bp.route("/users", methods=["GET"])
def get_users():

    zoom_account_id = request.args.get("zoom_account_id")
    if not zoom_account_id:
        return jsonify({"error": "zoom_account_id query parameter is required"}), 400

    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        return jsonify({"error": f"No active registration found for account {zoom_account_id}"}), 404

    search = request.args.get("search")

    try:
        users = get_zoom_users(account, search=search)
        return jsonify({
            "count": len(users),
            "users": users
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@zoom_bp.route("/encounter/<int:encounter_number>/fetch_zoom_note", methods=["POST"])
@verify_openemr_signature
def fetch_zoom_note(encounter_number: int):
    """
    Manually trigger a Zoom clinical note fetch and write it into an OpenEMR encounter.
 
    Called by the "Retrieve Note" button on the encounter page in OpenEMR.
    Handles the case where Zoom's webhook delivered an empty note_content
    on first delivery — the provider can edit in Zoom and then trigger this.

    Or, if the provider makes edits to the note in Zoom and wants the record in 
    OpenEMR updated, they can use that button to retrieve the updates. 
 
    Lookup chain:
        encounter_number
            → form_encounter.external_id (zoom_eid_{eid})
            → MeetingRecord.openemr_appointment_id = eid
            → MeetingRecord.clinical_note.zoom_note_id
            → get_zoom_clinical_note()
            → write_note_to_encounter()
 
    pid and provider_id are pulled directly from form_encounter
    since they are already stored there by create_encounter().
    """
 
    # --- 1. Look up form_encounter by encounter number ---
    # We need: external_id (to get eid), pid, provider_id
    engine = get_openemr_db_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT pid, provider_id, external_id
                    FROM form_encounter
                    WHERE encounter = :encounter
                    AND external_id LIKE 'zoom_eid_%'
                    LIMIT 1
                """),
                {"encounter": encounter_number}
            ).fetchone()
    except Exception as e:
        logger.error(f"fetch_zoom_note | DB error looking up encounter={encounter_number}: {e}")
        return jsonify({"error": "Database error looking up encounter"}), 500
 
    if not row:
        return jsonify({
            "error": f"No Zoom-linked encounter found for encounter number {encounter_number}"
        }), 404
 
    pid = row.pid
    provider_id = row.provider_id
    external_id = row.external_id  # e.g. "zoom_eid_42"
 
    # --- 2. Extract eid from external_id ---
    try:
        eid = int(external_id.removeprefix("zoom_eid_"))
    except ValueError:
        logger.error(f"fetch_zoom_note | Could not parse eid from external_id='{external_id}'")
        return jsonify({"error": f"Malformed external_id: {external_id}"}), 500
 
    # --- 3. Look up MeetingRecord by eid to get clinical_note.zoom_note_id + account ---
    record = MeetingRecord.query.filter_by(
        openemr_appointment_id=str(eid)
    ).first()
 
    if not record:
        return jsonify({
            "error": f"No MeetingRecord found for appointment eid={eid}"
        }), 404
 
    if not record.clinical_note or not record.clinical_note.zoom_note_id:
        return jsonify({
            "error": "No Zoom note ID on record — note webhook may not have arrived yet"
        }), 404
 
    # --- 4. Look up the ZoomAccount for this meeting record ---
    account = ZoomAccount.query.filter_by(
        id=record.zoom_account_id, is_active=True
    ).first()
 
    if not account:
        return jsonify({"error": "No active Zoom account found for this meeting"}), 404
 
    note_id = record.clinical_note.zoom_note_id
    # --- 5. Fetch the note from Zoom API ---
    try:
        note = get_zoom_clinical_note(account, note_id)
    except Exception as e:
        logger.error(f"fetch_zoom_note | Zoom API error for note_id={note_id}: {e}")
        return jsonify({"error": f"Failed to fetch note from Zoom: {str(e)}"}), 502
 
    note_content = note.get("note_content", "") if note is not None else "Note Content Missing"
    note_title = note.get("note_title", "Zoom Clinical Note") if note is not None else "Note Title Missing"

    # --- 6. Resolve provider username for forms table ---
    provider_username = get_provider_username(provider_id) or "admin"
 
    # --- 7. Write note into encounter ---
    success = write_note_to_encounter(
        encounter_number=encounter_number,
        pid=pid,
        provider_id=provider_id,
        provider_username=provider_username,
        note_content=note_content,
        note_title=note_title,
        note_id=note_id,
    )
 
    if not success:
        return jsonify({"error": "Failed to write note to encounter"}), 500
 
    logger.info(
        f"fetch_zoom_note | Written note_id={note_id} "
        f"to encounter={encounter_number} pid={pid}"
    )
    return jsonify({
        "status": "ok",
        "encounter_number": encounter_number,
        "note_id": note_id,
        "note_title": note_title,
    }), 200


@zoom_bp.route("/encounter/<int:encounter_number>/complete_zoom_note", methods=["POST"])
@verify_openemr_signature
def complete_zoom_note(encounter_number: int):
    """
    Mark a Zoom clinical note as completed.

    Called when a SOAP or Clinical Notes form is eSigned and locked in OpenEMR.
    Fire-and-forget from the browser — always returns 200 if the request is valid,
    regardless of whether the Zoom API call succeeds.

    Lookup chain:
        encounter_number
            → form_encounter.external_id (zoom_eid_{eid})
            → MeetingRecord.openemr_appointment_id = eid
            → MeetingRecord.clinical_note.zoom_note_id
            → mark_zoom_note_completed()

    Idempotent — if ClinicalNoteRecord.is_completed_in_zoom is already True,
    the Zoom API call is skipped.
    """

    # --- 1. Look up form_encounter by encounter number ---
    engine = get_openemr_db_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT pid, provider_id, external_id
                    FROM form_encounter
                    WHERE encounter = :encounter
                    AND external_id LIKE 'zoom_eid_%'
                    LIMIT 1
                """),
                {"encounter": encounter_number}
            ).fetchone()
    except Exception as e:
        logger.error(f"complete_zoom_note | DB error looking up encounter={encounter_number}: {e}")
        return jsonify({"status": "error", "reason": "database error"}), 200

    if not row:
        # Not a Zoom-linked encounter — silently succeed, nothing to do
        logger.info(f"complete_zoom_note | encounter={encounter_number} has no Zoom link, skipping")
        return jsonify({"status": "skipped", "reason": "not a zoom encounter"}), 200

    external_id = row.external_id

    # --- 2. Extract eid from external_id ---
    try:
        eid = int(external_id.removeprefix("zoom_eid_"))
    except ValueError:
        logger.error(f"complete_zoom_note | Could not parse eid from external_id='{external_id}'")
        return jsonify({"status": "error", "reason": "malformed external_id"}), 200

    # --- 3. Look up MeetingRecord ---
    record = MeetingRecord.query.filter_by(
        openemr_appointment_id=str(eid)
    ).first()

    if not record:
        logger.info(f"complete_zoom_note | No MeetingRecord for eid={eid}, skipping")
        return jsonify({"status": "skipped", "reason": "no meeting record"}), 200

    if not record.clinical_note or not record.clinical_note.zoom_note_id:
        logger.info(f"complete_zoom_note | No clinical note on record for eid={eid}, skipping")
        return jsonify({"status": "skipped", "reason": "no note on record"}), 200
    clinical_note = record.clinical_note
    # --- 4. Check idempotency ---
    if clinical_note.is_completed_in_zoom:
        logger.info(
            f"complete_zoom_note | note_id={clinical_note.zoom_note_id} "
            f"already completed, skipping"
        )
        write_audit_log(
            event_type="zoom.completion_skipped",
            success=True,
            zoom_account_id=record.account_id,
            zoom_note_id=clinical_note.zoom_note_id,
            openemr_appointment_id=str(eid),
        )
        return jsonify({"status": "already_completed"}), 200

    # --- 5. Look up ZoomAccount ---
    account = ZoomAccount.query.filter_by(
        id=record.zoom_account_id, is_active=True
    ).first()

    if not account:
        logger.error(f"complete_zoom_note | No active ZoomAccount for eid={eid}")
        return jsonify({"status": "error", "reason": "no zoom account"}), 200

    # --- 6. Mark note completed in Zoom ---
    try:
        mark_zoom_note_completed(account, clinical_note.zoom_note_id)
    except Exception as e:
        logger.error(f"complete_zoom_note | Zoom API error for note_id={clinical_note.zoom_note_id}: {e}")
        write_audit_log(
            event_type="zoom.completion_error",
            success=False,
            zoom_account_id=account.account_id,
            zoom_note_id=clinical_note.zoom_note_id,
            openemr_appointment_id=str(eid),
            error_message=str(e),
        )
        return jsonify({"status": "error", "reason": "zoom api error"}), 200

    # --- 7. Update ClinicalNoteRecord ---
    try:
        record.clinical_note.is_completed_in_zoom = True
        record.clinical_note.completed_in_zoom_at = datetime.now(timezone.utc)
        db.session.commit()

        write_audit_log(
            event_type="zoom.completion_success",
            success=True,
            zoom_account_id=account.account_id,
            zoom_note_id=clinical_note.zoom_note_id,
            openemr_appointment_id=str(eid),
            detail={"encounter": encounter_number}
        )
    except Exception as e:
        logger.error(f"complete_zoom_note | Failed to update ClinicalNoteRecord for note_id={clinical_note.zoom_note_id}: {e}")
        return jsonify({"status": "error", "reason": "db update failed"}), 200

    logger.info(
        f"complete_zoom_note | Marked note_id={clinical_note.zoom_note_id} completed "
        f"for encounter={encounter_number} eid={eid}"
    )
    return jsonify({"status": "completed", "note_id": clinical_note.zoom_note_id}), 200
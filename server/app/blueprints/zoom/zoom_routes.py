import logging
from datetime import datetime, timezone
from sqlalchemy import text
from flask import jsonify, request
from app.models import ZoomAccount, MeetingRecord
from app.extensions import db, get_openemr_db_engine
from app.services.audit import write_audit_log
from app.services.zoom import get_zoom_users, get_zoom_clinical_note, mark_zoom_note_completed
from app.services.openemr import write_note_to_encounter, get_provider_username

from app.blueprints.zoom.zoom_route_helper import verify_openemr_signature, _audit_manual_fetch_failed
from app.blueprints.zoom import zoom_bp

logger = logging.getLogger(__name__)


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
    logger.info(f"fetch_zoom_note | manual fetch requested encounter={encounter_number}")
    write_audit_log(
        event_type="note.manual_fetch_requested",
        success=True,
        openemr_encounter_number=str(encounter_number),
    )

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
        _audit_manual_fetch_failed(
            reason="db_error",
            error_message=str(e),
            encounter_number=encounter_number,
        )
        return jsonify({"error": "Database error looking up encounter"}), 500

    if not row:
        logger.warning(
            f"fetch_zoom_note | No Zoom-linked encounter for encounter={encounter_number}"
        )
        _audit_manual_fetch_failed(
            reason="not_zoom_encounter",
            error_message="no zoom-linked encounter",
            encounter_number=encounter_number,
        )
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
        _audit_manual_fetch_failed(
            reason="malformed_external_id",
            error_message=f"malformed external_id: {external_id}",
            encounter_number=encounter_number,
            openemr_provider_id=str(provider_id) if provider_id is not None else None,
            openemr_patient_id=str(pid) if pid is not None else None,
        )
        return jsonify({"error": f"Malformed external_id: {external_id}"}), 500

    # --- 3. Look up MeetingRecord by eid to get clinical_note.zoom_note_id + account ---
    record = MeetingRecord.query.filter_by(
        openemr_appointment_id=str(eid)
    ).first()

    if not record:
        logger.warning(
            f"fetch_zoom_note | No MeetingRecord for eid={eid} encounter={encounter_number}"
        )
        _audit_manual_fetch_failed(
            reason="no_meeting_record",
            error_message="no meeting record",
            encounter_number=encounter_number,
            openemr_appointment_id=str(eid),
            openemr_provider_id=str(provider_id) if provider_id is not None else None,
            openemr_patient_id=str(pid) if pid is not None else None,
        )
        return jsonify({
            "error": f"No MeetingRecord found for appointment eid={eid}"
        }), 404

    if not record.clinical_note or not record.clinical_note.zoom_note_id:
        logger.warning(f"fetch_zoom_note | No zoom_note_id on record eid={eid}")
        _audit_manual_fetch_failed(
            reason="no_note_id",
            error_message="no zoom_note_id on record",
            encounter_number=encounter_number,
            zoom_account_id=record.zoom_account_id,
            openemr_appointment_id=str(eid),
            openemr_provider_id=str(provider_id) if provider_id is not None else None,
            openemr_patient_id=str(pid) if pid is not None else None,
            zoom_meeting_id=record.zoom_meeting_id,
        )
        return jsonify({
            "error": "No Zoom note ID on record — note webhook may not have arrived yet"
        }), 404

    # --- 4. Look up the ZoomAccount for this meeting record ---
    account = ZoomAccount.query.filter_by(
        account_id=record.zoom_account_id, is_active=True
    ).first()

    if not account:
        logger.warning(
            f"fetch_zoom_note | No active ZoomAccount for record account_id={record.zoom_account_id}"
        )
        _audit_manual_fetch_failed(
            reason="account_inactive",
            error_message="no active zoom account",
            encounter_number=encounter_number,
            zoom_account_id=record.zoom_account_id,
            openemr_appointment_id=str(eid),
            openemr_provider_id=str(provider_id) if provider_id is not None else None,
            openemr_patient_id=str(pid) if pid is not None else None,
            zoom_meeting_id=record.zoom_meeting_id,
            zoom_note_id=record.clinical_note.zoom_note_id,
        )
        return jsonify({"error": "No active Zoom account found for this meeting"}), 404

    note_id = record.clinical_note.zoom_note_id

    # --- 5. Fetch the note from Zoom API ---
    try:
        note = get_zoom_clinical_note(account, note_id)
    except Exception as e:
        logger.error(f"fetch_zoom_note | Zoom API error for note_id={note_id}: {e}")
        write_audit_log(
            event_type="note.fetch_error",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=str(eid),
            openemr_encounter_number=str(encounter_number),
            openemr_provider_id=str(provider_id) if provider_id is not None else None,
            openemr_patient_id=str(pid) if pid is not None else None,
            zoom_meeting_id=record.zoom_meeting_id,
            zoom_note_id=note_id,
            error_message=str(e),
            detail={"trigger": "manual_fetch"},
        )
        return jsonify({"error": f"Failed to fetch note from Zoom: {str(e)}"}), 502

    # --- 5a. Inspect content shape (G-M9) ---
    note_none = note is None
    raw_content = note.get("note_content", "") if note is not None else ""
    raw_title = note.get("note_title", "Zoom Clinical Note") if note is not None else "Note Title Missing"
    content_length = len(raw_content)
    stripped_length = len(raw_content.strip()) if raw_content else 0
    content_blank = stripped_length == 0

    logger.info(
        f"fetch_zoom_note | content shape note_id={note_id} note_none={note_none} "
        f"content_length={content_length} stripped_length={stripped_length}"
    )

    if content_blank:
        write_audit_log(
            event_type="note.content_empty",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=str(eid),
            openemr_encounter_number=str(encounter_number),
            openemr_provider_id=str(provider_id) if provider_id is not None else None,
            openemr_patient_id=str(pid) if pid is not None else None,
            zoom_meeting_id=record.zoom_meeting_id,
            zoom_note_id=note_id,
            error_message="note not found in Zoom API" if note_none else "note content empty",
            detail={
                "trigger": "manual_fetch",
                "note_none": note_none,
                "content_length": content_length,
            },
        )

    # Preserve current behavior: placeholder body when Zoom returned None.
    note_content = raw_content if not note_none else "Note Content Missing"
    note_title = raw_title

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
        note_writeback_mode=account.config.note_writeback_mode if account.config else "both",
    )

    write_audit_log(
        event_type="note.written" if success else "note.write_failed",
        success=success,
        zoom_account_id=account.account_id,
        openemr_appointment_id=str(eid),
        openemr_encounter_number=str(encounter_number),
        openemr_provider_id=str(provider_id) if provider_id is not None else None,
        openemr_patient_id=str(pid) if pid is not None else None,
        zoom_meeting_id=record.zoom_meeting_id,
        zoom_note_id=note_id,
        error_message=None if success else "OpenEMR note write failed",
        detail={"trigger": "manual_fetch", "content_blank": content_blank},
    )

    if not success:
        return jsonify({"error": "Failed to write note to encounter"}), 500

    logger.info(
        f"fetch_zoom_note | Written note_id={note_id} "
        f"to encounter={encounter_number} pid={pid} content_blank={content_blank}"
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
            zoom_account_id=record.zoom_account_id,
            zoom_note_id=clinical_note.zoom_note_id,
            openemr_appointment_id=str(eid),
            openemr_encounter_number=str(encounter_number),
            openemr_provider_id=row.provider_id,
            openemr_patient_id=row.pid,
        )
        return jsonify({"status": "already_completed"}), 200

    # --- 5. Look up ZoomAccount ---
    account = ZoomAccount.query.filter_by(
        account_id=record.zoom_account_id, is_active=True
    ).first()

    if not account:
        logger.error(f"complete_zoom_note | No active ZoomAccount for eid={eid}")
        return jsonify({"status": "error", "reason": "no zoom account"}), 200

    # --- 6. Mark note completed in Zoom ---
    try:
        completion_success = mark_zoom_note_completed(account, clinical_note.zoom_note_id)
    except Exception as e:
        logger.error(f"complete_zoom_note | Zoom API error for note_id={clinical_note.zoom_note_id}: {e}")
        write_audit_log(
            event_type="zoom.completion_error",
            success=False,
            zoom_account_id=account.account_id,
            zoom_note_id=clinical_note.zoom_note_id,
            openemr_appointment_id=str(eid),
            openemr_encounter_number=str(encounter_number),
            openemr_provider_id=row.provider_id,
            openemr_patient_id=row.pid,
            error_message=str(e),
        )
        return jsonify({"status": "error", "reason": "zoom api error"}), 200
    if not completion_success:
        logger.error(f"complete_zoom_note | Zoom API returned failure for note_id={clinical_note.zoom_note_id}")
        write_audit_log(
            event_type="zoom.completion_error",
            success=False,
            zoom_account_id=account.account_id,
            zoom_note_id=clinical_note.zoom_note_id,
            openemr_appointment_id=str(eid),
            openemr_encounter_number=str(encounter_number),
            openemr_provider_id=row.provider_id,
            openemr_patient_id=row.pid,
            error_message="Zoom note completion failed",
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
            openemr_encounter_number=str(encounter_number),
            openemr_provider_id=row.provider_id,
            openemr_patient_id=row.pid,
        )
    except Exception as e:
        logger.error(f"complete_zoom_note | Failed to update ClinicalNoteRecord for note_id={clinical_note.zoom_note_id}: {e}")
        return jsonify({"status": "error", "reason": "db update failed"}), 200

    logger.info(
        f"complete_zoom_note | Marked note_id={clinical_note.zoom_note_id} completed "
        f"for encounter={encounter_number} eid={eid}"
    )
    return jsonify({"status": "completed", "note_id": clinical_note.zoom_note_id}), 200

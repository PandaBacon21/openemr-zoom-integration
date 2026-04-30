import logging
from datetime import datetime, timezone
from flask import request, jsonify
from app.models import AuditLog
from app.blueprints.audit import audit_bp

logger = logging.getLogger(__name__)


@audit_bp.route("/logs", methods=["GET"])
def get_audit_logs():
    """
    Return paginated, filterable audit log entries.

    Query parameters (all optional):
        zoom_account_id         — filter to a specific account
        event_type              — filter by event type string
        openemr_appointment_id  — filter by appointment ID
        openemr_encounter_number— filter by encounter number
        zoom_meeting_id         — filter by Zoom meeting ID
        zoom_note_id            — filter by Zoom note ID
        success                 — filter by success (true/false)
        date_from               — ISO datetime lower bound
        date_to                 — ISO datetime upper bound
        page                    — page number (default 1)
        per_page                — page size (default 50, max 200)
    """

    query = AuditLog.query

    # Filters
    zoom_account_id = request.args.get("zoom_account_id")
    if zoom_account_id:
        query = query.filter(AuditLog.zoom_account_id == zoom_account_id)

    event_type = request.args.get("event_type")
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)

    openemr_appointment_id = request.args.get("openemr_appointment_id")
    if openemr_appointment_id:
        query = query.filter(AuditLog.openemr_appointment_id == openemr_appointment_id)

    openemr_encounter_number = request.args.get("openemr_encounter_number")
    if openemr_encounter_number:
        query = query.filter(AuditLog.openemr_encounter_number == openemr_encounter_number)

    zoom_meeting_id = request.args.get("zoom_meeting_id")
    if zoom_meeting_id:
        query = query.filter(AuditLog.zoom_meeting_id == zoom_meeting_id)

    zoom_note_id = request.args.get("zoom_note_id")
    if zoom_note_id:
        query = query.filter(AuditLog.zoom_note_id == zoom_note_id)

    success = request.args.get("success")
    if success is not None:
        query = query.filter(AuditLog.success == (success.lower() == "true"))

    date_from = request.args.get("date_from")
    if date_from:
        try:
            query = query.filter(
                AuditLog.occurred_at >= datetime.fromisoformat(date_from)
            )
        except ValueError:
            return jsonify({"error": f"Invalid date_from format: {date_from}"}), 400

    date_to = request.args.get("date_to")
    if date_to:
        try:
            query = query.filter(
                AuditLog.occurred_at <= datetime.fromisoformat(date_to)
            )
        except ValueError:
            return jsonify({"error": f"Invalid date_to format: {date_to}"}), 400

    # Pagination
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    # Order by most recent first
    query = query.order_by(AuditLog.occurred_at.desc())

    total = query.count()
    logs = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),  # ceiling division
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "zoom_account_id": log.zoom_account_id,
                "openemr_appointment_id": log.openemr_appointment_id,
                "openemr_encounter_number": log.openemr_encounter_number,
                "openemr_provider_id": log.openemr_provider_id,
                "openemr_patient_id": log.openemr_patient_id,
                "zoom_meeting_id": log.zoom_meeting_id,
                "zoom_note_id": log.zoom_note_id,
                "success": log.success,
                "error_message": log.error_message,
                "detail": log.detail,
                "occurred_at": log.occurred_at.isoformat(),
            }
            for log in logs
        ]
    }), 200
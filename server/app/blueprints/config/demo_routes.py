"""
Sprint 13 demo orchestration routes.

Lives under the config blueprint (`/config/demo/*`) because these are SE-facing
admin actions tied to a registered ZoomAccount, alongside provider/filter
management. URL shape: POST /config/demo/hydrate
"""

import logging

from flask import request, jsonify

from app.models import ZoomAccount
from app.services.audit import write_audit_log
from app.services.hydrate import hydrate_future_meetings
from app.services.openemr import seed_past_locked_encounters

from app.blueprints.config import config_bp


logger = logging.getLogger(__name__)


@config_bp.route("/demo/hydrate", methods=["POST"])
def hydrate_demo_data():
    """
    Run the hydration orchestrator for the supplied ZoomAccount. Each mapped
    provider's next 4 weekday slots (tomorrow 9am/2pm + day-after 9am/2pm)
    get an appointment + real Zoom meeting. Idempotent — re-running tops up
    any missing pieces without duplicating existing state.
    """
    data = request.get_json(silent=True) or {}
    zoom_account_id = data.get("zoom_account_id")
    if not zoom_account_id:
        return jsonify({"error": "zoom_account_id is required in the request body"}), 400

    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        write_audit_log(
            event_type="demo.hydrate_request_failed",
            success=False,
            zoom_account_id=zoom_account_id,
            error_message="No active registration found",
            detail={"stage": "account_lookup"},
        )
        return jsonify({"error": f"No active registration found for account {zoom_account_id}"}), 404

    try:
        future_summary = hydrate_future_meetings(account)
        past_summary = seed_past_locked_encounters(account)
    except Exception as exc:
        logger.exception(
            f"config.demo.hydrate | account={zoom_account_id} orchestrator raised"
        )
        write_audit_log(
            event_type="demo.hydrate_request_failed",
            success=False,
            zoom_account_id=zoom_account_id,
            error_message=str(exc),
            detail={"stage": "orchestrator"},
        )
        return jsonify({"error": str(exc)}), 500

    # Merge — the two passes don't share any keys.
    return jsonify({**future_summary, **past_summary}), 200

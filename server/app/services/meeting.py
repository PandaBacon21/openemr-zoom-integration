"""
Service layer for binding an OpenEMR appointment to a Zoom meeting.

Bridges two domains, so it lives at the top level of services/ alongside
audit.py and keys.py rather than inside services/openemr/ or services/zoom/.
(See follow-up backlog item — broader services-layout review planned.)

Used by:
  - Production path: the `appointment.created` webhook handler in
    blueprints/webhooks/openemr/openemr_webhook_helpers._process_appointment_event,
    where a UI-created appointment fires through here to mint its Zoom
    meeting + MeetingRecord.
  - Hydration path: the Sprint 13 demo hydration orchestrator, which
    constructs a synthetic AppointmentMatch + payload for each mapped
    provider's empty/incomplete slot and calls this same function so the
    demo data ends up indistinguishable from real webhook-driven state.
"""

import logging

from flask import current_app

from app.services.zoom import create_zoom_meeting
from app.services.openemr.appointments.appointment import write_zoom_urls_to_appointment
from app.services.audit import write_audit_log
from app.extensions import db
from app.models import MeetingRecord, MeetingPatient


logger = logging.getLogger(__name__)


def create_meeting_for_appointment(match, payload: dict) -> dict:
    """
    Create a new Zoom meeting for the appointment described by (match, payload),
    persist MeetingRecord + MeetingPatient, write the Zoom URL back to the
    OpenEMR appointment row, and emit audit events at each step.

    Args:
        match:   AppointmentMatch (zoom_account + provider_mapping + payload)
        payload: Appointment event dict — used here for eid / pid / appt_status

    Returns:
        On success:
          {"account_id": ..., "zoom_meeting_id": ..., "zoom_join_url": ..., "zoom_start_url": ...}
        On failure:
          {"error": "<message>"}
    """
    account = match.zoom_account
    mapping = match.provider_mapping
    eid = payload.get("eid")

    try:
        meeting_data = create_zoom_meeting(match)
    except Exception as e:
        current_app.logger.error(
            f"meeting_service | eid={eid} account={account.account_id} "
            f"Zoom meeting creation failed: {e}"
        )
        write_audit_log(
            event_type="meeting.create_failed",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            openemr_user_id=mapping.openemr_user_id,
            openemr_patient_id=payload.get("pid"),
            error_message=str(e),
            detail={"stage": "zoom_create"},
        )
        return {"error": str(e)}

    try:
        meeting_record = MeetingRecord(
            zoom_account_id=account.account_id,
            zoom_meeting_id=meeting_data["meeting_id"],
            zoom_start_url=meeting_data["start_url"],
            zoom_join_url=meeting_data["join_url"],
            openemr_appointment_id=str(eid),
            openemr_user_id=str(mapping.openemr_user_id),
            openemr_appt_status=payload.get("appt_status"),
            status="created",
        )
        db.session.add(meeting_record)
        db.session.flush()

        pid = payload.get("pid")
        if pid:
            db.session.add(MeetingPatient(
                zoom_meeting_id=meeting_data["meeting_id"],
                openemr_patient_id=str(pid),
            ))

        db.session.commit()

        current_app.logger.info(
            f"meeting_service | eid={eid} account={account.account_id} "
            f"MeetingRecord created zoom_meeting_id={meeting_data['meeting_id']}"
        )
        write_audit_log(
            event_type="meeting.created",
            success=True,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            openemr_user_id=mapping.openemr_user_id,
            zoom_meeting_id=meeting_data["meeting_id"],
        )

        # Write Zoom URLs back to OpenEMR appointment record
        if eid:
            success = write_zoom_urls_to_appointment(
                eid=eid,
                start_url=meeting_data["start_url"],
                join_url=meeting_data["join_url"],
            )

            current_app.logger.info(
                f"meeting_service | eid={eid} account={account.account_id} "
                f"{'Meeting link written back to OpenEMR' if success else 'Meeting link failed to write back to OpenEMR'} "
                f"zoom_meeting_id={meeting_data['meeting_id']}"
            )

            write_audit_log(
                event_type="openemr.url_writeback_success" if success else "openemr.url_writeback_failed",
                success=success,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                openemr_user_id=mapping.openemr_user_id,
                openemr_patient_id=pid,
                zoom_meeting_id=meeting_data["meeting_id"],
                error_message=None if success else "Zoom URL writeback failed",
            )

        return {
            "account_id": account.account_id,
            "zoom_meeting_id": meeting_data["meeting_id"],
            "zoom_join_url": meeting_data["join_url"],
            "zoom_start_url": meeting_data["start_url"],
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"meeting_service | eid={eid} account={account.account_id} "
            f"DB write failed: {e}"
        )
        write_audit_log(
            event_type="meeting.create_failed",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            openemr_user_id=mapping.openemr_user_id,
            openemr_patient_id=payload.get("pid"),
            zoom_meeting_id=meeting_data.get("meeting_id"),
            error_message=str(e),
            detail={"stage": "local_record_create"},
        )

        return {"error": str(e)}

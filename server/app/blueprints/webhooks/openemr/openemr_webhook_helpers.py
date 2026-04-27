import hashlib
import hmac
from flask import current_app
from app.services.zoom import (create_zoom_meeting, get_zoom_meeting, update_zoom_meeting, 
                               delete_zoom_meeting)
from app.services.openemr import (write_zoom_urls_to_appointment, filter_appointment_event)
from app.services.audit import write_audit_log
from app.extensions import db
from app.models import MeetingRecord, MeetingPatient


# ---------------------------------------------------------------------------
# Signature verification helper
# ---------------------------------------------------------------------------

def _verify_signature(body: bytes, received_sig: str, secret: str) -> bool:
    """
    Recompute HMAC-SHA256 over the raw request body and compare
    against the signature sent in the X-Zoomly-Signature header.

    Uses hmac.compare_digest() for a timing-safe comparison —
    prevents timing attacks that could leak the secret one bit at a time.

    Args:
        body:         Raw request bytes (request.data)
        received_sig: Hex digest from the X-Zoomly-Signature header
        secret:       OPENEMR_FLASK_SECRET from app config

    Returns:
        True if signatures match, False otherwise.
    """
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, received_sig)


# ---------------------------------------------------------------------------
# Create/Update handler
# ---------------------------------------------------------------------------

def _process_appointment_event(payload: dict) -> tuple[dict, int]:
    """
    Orchestrates the appointment event pipeline:
      S4-03: Filter — check provider mapping + appointment type mapping  ✓
      S4-04: Zoom API — create meeting with provider as host             ✓
      S4-05: Store MeetingRecord + MeetingPatient                        ✓
      S4-06: Error handling
      S4-07: Write AuditLog entry

    Args:
        payload: Validated, parsed appointment event dict from OpenEMR.

    Returns:
        (response_body_dict, http_status_code)
    """
    eid = payload.get("eid")

    # Filter
    matches = filter_appointment_event(payload)

    if not matches:
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} dropped — no matching account/provider/type"
        )
        write_audit_log(
            event_type="appointment.dropped",
            success=True,
            openemr_appointment_id=eid,
            detail={"reason": "no matching provider/type", "appointment_type": payload.get("category_id")},
        )
        return {"status": "dropped", "eid": eid}, 200

    current_app.logger.info(
        f"webhooks.openemr | eid={eid} matched {len(matches)} account(s), proceeding"
    )
    created_meetings = []
    updated_meetings = []
    errors = []
 
    for match in matches:
        account = match.zoom_account
        # mapping = match.provider_mapping

        # Check for existing MeetingRecord
        existing_meeting_record = MeetingRecord.query.filter_by(
            openemr_appointment_id=str(eid),
            zoom_account_id=account.id
        ).first()

        if existing_meeting_record:
            # Update path
            result = _handle_existing_meeting(
                existing_meeting_record, match, payload
            )
            if result.get("error"):
                errors.append({
                    "account_id": account.account_id,
                    "error": result["error"]
                })
            else:
                updated_meetings.append(result)
        else:
            # Create path
            result = _handle_new_meeting(match, payload)
            if result.get("error"):
                errors.append({
                    "account_id": account.account_id,
                    "error": result["error"]
                })
            else:
                created_meetings.append(result)
 
    # Build response
    if not created_meetings and not updated_meetings and errors:
        return {"status": "error", "eid": eid, "errors": errors}, 500
 
    if (created_meetings or updated_meetings) and errors:
        return {
            "status": "partial",
            "eid": eid,
            "created": created_meetings,
            "updated": updated_meetings,
            "errors": errors
        }, 207
 
    return {
        "status": "ok",
        "eid": eid,
        "created": created_meetings,
        "updated": updated_meetings,
    }, 200
 

def _handle_new_meeting(match, payload: dict) -> dict:
    """Create a new Zoom meeting and MeetingRecord."""
    account = match.zoom_account
    mapping = match.provider_mapping
    eid = payload.get("eid")
 
    try:
        meeting_data = create_zoom_meeting(match)
    except Exception as e:
        current_app.logger.error(
            f"webhooks.openemr | eid={eid} account={account.account_id} "
            f"Zoom meeting creation failed: {e}"
        )
        return {"error": str(e)}
 
    try:
        meeting_record = MeetingRecord(
            zoom_account_id=account.id,
            zoom_meeting_id=meeting_data["meeting_id"],
            zoom_start_url=meeting_data["start_url"],
            zoom_join_url=meeting_data["join_url"],
            openemr_appointment_id=str(eid),
            openemr_provider_id=str(mapping.openemr_provider_id),
            openemr_appt_status=payload.get("appt_status"),
            status="created",
        )
        db.session.add(meeting_record)
        db.session.flush()
 
        pid = payload.get("pid")
        if pid:
            db.session.add(MeetingPatient(
                meeting_record_id=meeting_record.id,
                openemr_patient_id=str(pid),
            ))
 
        db.session.commit()
 
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} account={account.account_id} "
            f"MeetingRecord created id={meeting_record.id} "
            f"zoom_meeting_id={meeting_data['meeting_id']}"
        )
        write_audit_log(
            event_type="meeting.created",
            success=True,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            openemr_provider_id=mapping.openemr_provider_id,
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
                f"webhooks.openemr | eid={eid} account={account.account_id} "
                f"{'Meeting link written back to OpenEMR' if success else 'Meeting link failed to write back to OpenEMR'} "
                f"zoom_meeting_id={meeting_data['meeting_id']}"
            )

            write_audit_log(
                event_type="openemr.url_writeback_success" if success else "openemr.url_writeback_failed",
                success=success,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=meeting_data["meeting_id"],
            )   
 
        return {
            "account_id": account.account_id,
            "zoom_meeting_id": meeting_data["meeting_id"],
            "zoom_join_url": meeting_data["join_url"],
            "zoom_start_url": meeting_data["start_url"],
            "meeting_record_id": meeting_record.id,
        }
 
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"webhooks.openemr | eid={eid} account={account.account_id} "
            f"DB write failed: {e}"
        )
        write_audit_log(
            event_type="meeting.create_failed",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            error_message=str(e),
        )

        return {"error": str(e)}
 
 
def _handle_existing_meeting(
    record: MeetingRecord,
    match,
    payload: dict
) -> dict:
    """
    Handle an appointment event when a MeetingRecord already exists.
 
    Checks if the Zoom meeting still exists:
    - If deleted in Zoom → create a new meeting, update the record
    - If exists → patch the meeting with updated fields, update the record
    """
    account = match.zoom_account
    eid = payload.get("eid")
 
    current_app.logger.info(
        f"webhooks.openemr | eid={eid} existing MeetingRecord id={record.id} "
        f"zoom_meeting_id={record.zoom_meeting_id} — checking Zoom"
    )
 
    # Check if meeting still exists in Zoom
    try:
        zoom_meeting = get_zoom_meeting(account, record.zoom_meeting_id)
    except Exception as e:
        current_app.logger.error(
            f"webhooks.openemr | eid={eid} failed to check Zoom meeting "
            f"{record.zoom_meeting_id}: {e}"
        )
        return {"error": str(e)}
 
    if zoom_meeting is None:
        # Meeting was deleted in Zoom — create a new one
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} Zoom meeting {record.zoom_meeting_id} "
            "no longer exists — creating replacement"
        )
        try:
            meeting_data = create_zoom_meeting(match)
        except Exception as e:
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} replacement meeting creation failed: {e}"
            )
            return {"error": str(e)}
 
        try:
            record.zoom_meeting_id = meeting_data["meeting_id"]
            record.zoom_start_url = meeting_data["start_url"]
            record.zoom_join_url = meeting_data["join_url"]
            record.openemr_appt_status = payload.get("appt_status")
            record.status = "created"
            db.session.commit()
 
            current_app.logger.info(
                f"webhooks.openemr | eid={eid} MeetingRecord id={record.id} "
                f"updated with new zoom_meeting_id={meeting_data['meeting_id']}"
            )
            write_audit_log(
                event_type="meeting.recreated",
                success=True,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=meeting_data["meeting_id"],
            )

            # Write new URLs back to OpenEMR appointment record
            if eid:
                success = write_zoom_urls_to_appointment(
                    eid=eid,
                    start_url=meeting_data["start_url"],
                    join_url=meeting_data["join_url"],
                )

                current_app.logger.info(
                    f"webhooks.openemr | eid={eid} account={account.account_id} "
                    f"{'Meeting link written back to OpenEMR' if success else 'Meeting link failed to write back to OpenEMR'} "
                    f"zoom_meeting_id={meeting_data['meeting_id']}"
                )

                write_audit_log(
                    event_type="openemr.url_writeback_success" if success else "openemr.url_writeback_failed",
                    success=success,
                    zoom_account_id=account.account_id,
                    openemr_appointment_id=eid,
                    zoom_meeting_id=meeting_data["meeting_id"],
                )
 
            return {
                "account_id": account.account_id,
                "zoom_meeting_id": meeting_data["meeting_id"],
                "zoom_join_url": meeting_data["join_url"],
                "zoom_start_url": meeting_data["start_url"],
                "meeting_record_id": record.id,
                "action": "recreated",
            }
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}
 
    else:
        # Meeting exists — patch it with updated fields
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} Zoom meeting {record.zoom_meeting_id} "
            "exists — updating"
        )
        try:
            update_zoom_meeting(account, record.zoom_meeting_id, match)
        except Exception as e:
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} failed to update Zoom meeting "
                f"{record.zoom_meeting_id}: {e}"
            )
            return {"error": str(e)}
 
        try:
            record.openemr_appt_status = payload.get("appt_status")
            db.session.commit()
 
            current_app.logger.info(
                f"webhooks.openemr | eid={eid} MeetingRecord id={record.id} updated"
            )
            write_audit_log(
                event_type="meeting.updated",
                success=True,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=record.zoom_meeting_id,
            )
 
            return {
                "account_id": account.account_id,
                "zoom_meeting_id": record.zoom_meeting_id,
                "zoom_join_url": record.zoom_join_url,
                "zoom_start_url": record.zoom_start_url,
                "meeting_record_id": record.id,
                "action": "updated",
            }
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}


# ---------------------------------------------------------------------------
# Delete handler
# ---------------------------------------------------------------------------
 
def _process_appointment_delete(payload: dict) -> tuple[dict, int]:
    """
    Handle appointment.deleted events from OpenEMR.
 
    Looks up MeetingRecord by eid, deletes the Zoom meeting,
    and removes the local record.
    """
    eid = payload.get("eid")
 
    # Find all meeting records for this appointment
    # (could be multiple if multi-account, but typically one)
    records = MeetingRecord.query.filter_by(
        openemr_appointment_id=str(eid)
    ).all()
 
    if not records:
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} delete event received but no MeetingRecord found — nothing to do"
        )
        return {"status": "no_record", "eid": eid}, 200
 
    deleted_meetings = []
    errors = []
 
    for record in records:
        account = record.zoom_account
        meeting_id = record.zoom_meeting_id
 
        # Delete from Zoom
        try:
            delete_zoom_meeting(account, meeting_id)
        except Exception as e:
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} failed to delete Zoom meeting "
                f"{meeting_id}: {e}"
            )
            errors.append({"meeting_id": meeting_id, "error": str(e)})
            # Mark record as error but continue — still remove from DB
            record.status = "error"
            db.session.commit()
            continue
 
        # Remove from DB — cascade deletes MeetingPatient rows
        try:
            db.session.delete(record)
            db.session.commit()
            current_app.logger.info(
                f"webhooks.openemr | eid={eid} MeetingRecord id={record.id} "
                f"and Zoom meeting {meeting_id} deleted"
            )
            write_audit_log(
                event_type="meeting.deleted",
                success=True,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=meeting_id,
            )
            deleted_meetings.append(meeting_id)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} failed to delete MeetingRecord "
                f"id={record.id}: {e}"
            )
            write_audit_log(
                event_type="meeting.delete_failed",
                success=False,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=meeting_id,
                error_message=str(e),
            )
            errors.append({"meeting_id": meeting_id, "error": str(e)})
 
    if errors and not deleted_meetings:
        return {"status": "error", "eid": eid, "errors": errors}, 500
 
    return {
        "status": "deleted",
        "eid": eid,
        "deleted_meetings": deleted_meetings
    }, 200



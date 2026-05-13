import hashlib
import hmac
from flask import current_app
from app.services.zoom import (create_zoom_meeting, get_zoom_meeting, update_zoom_meeting, 
                               delete_zoom_meeting)
from app.services.openemr import (write_zoom_urls_to_appointment, filter_appointment_event)
from app.services.audit import write_audit_log
from app.extensions import db
from app.models import MeetingRecord, MeetingPatient, ZoomAccount


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
    matches, drop_reason = filter_appointment_event(payload)

    if not matches:
        current_app.logger.info(
            f"webhooks.openemr | eid={eid} dropped — reason={drop_reason}"
        )
        write_audit_log(
            event_type="appointment.dropped",
            success=True,
            openemr_appointment_id=eid,
            detail={"reason": drop_reason, "appointment_type": payload.get("category_id")},
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
            zoom_account_id=account.account_id
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
        write_audit_log(
            event_type="meeting.create_failed",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            openemr_provider_id=mapping.openemr_provider_id,
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
            openemr_provider_id=str(mapping.openemr_provider_id),
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
            f"webhooks.openemr | eid={eid} account={account.account_id} "
            f"MeetingRecord created zoom_meeting_id={meeting_data['meeting_id']}"
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
                openemr_provider_id=mapping.openemr_provider_id,
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
            f"webhooks.openemr | eid={eid} account={account.account_id} "
            f"DB write failed: {e}"
        )
        write_audit_log(
            event_type="meeting.create_failed",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            openemr_provider_id=mapping.openemr_provider_id,
            openemr_patient_id=payload.get("pid"),
            zoom_meeting_id=meeting_data.get("meeting_id"),
            error_message=str(e),
            detail={"stage": "local_record_create"},
        )

        return {"error": str(e)}
 
 
def _handle_existing_meeting(
    record: MeetingRecord,
    match,
    payload: dict
) -> dict:
    account = match.zoom_account
    mapping = match.provider_mapping
    eid = payload.get("eid")
    payload_pid = payload.get("pid")

    current_app.logger.info(
        f"webhooks.openemr | eid={eid} existing MeetingRecord "
        f"zoom_meeting_id={record.zoom_meeting_id} — checking Zoom"
    )

    try:
        zoom_meeting = get_zoom_meeting(account, record.zoom_meeting_id)
    except Exception as e:
        current_app.logger.error(
            f"webhooks.openemr | eid={eid} failed to check Zoom meeting "
            f"{record.zoom_meeting_id}: {e}"
        )
        write_audit_log(
            event_type="meeting.update_failed",
            success=False,
            zoom_account_id=account.account_id,
            openemr_appointment_id=eid,
            openemr_provider_id=mapping.openemr_provider_id,
            openemr_patient_id=payload_pid,
            zoom_meeting_id=record.zoom_meeting_id,
            error_message=str(e),
            detail={"stage": "zoom_lookup"},
        )
        return {"error": str(e)}

    if zoom_meeting is None:
        # Meeting was deleted in Zoom — delete old record, create new one
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
            write_audit_log(
                event_type="meeting.recreate_failed",
                success=False,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                openemr_provider_id=mapping.openemr_provider_id,
                openemr_patient_id=payload_pid,
                zoom_meeting_id=record.zoom_meeting_id,
                error_message=str(e),
                detail={"stage": "zoom_create_replacement"},
            )
            return {"error": str(e)}

        try:
            old_meeting_id = record.zoom_meeting_id
            pid = None
            old_patient = MeetingPatient.query.filter_by(
                zoom_meeting_id=old_meeting_id
            ).first()
            if old_patient:
                pid = old_patient.openemr_patient_id

            db.session.delete(record)

            new_record = MeetingRecord(
                zoom_account_id=account.account_id,
                zoom_meeting_id=meeting_data["meeting_id"],
                zoom_start_url=meeting_data["start_url"],
                zoom_join_url=meeting_data["join_url"],
                openemr_appointment_id=str(eid),
                openemr_provider_id=mapping.openemr_provider_id,
                openemr_appt_status=payload.get("appt_status"),
                status="created",
            )
            db.session.add(new_record)

            if pid:
                db.session.add(MeetingPatient(
                    zoom_meeting_id=meeting_data["meeting_id"],
                    openemr_patient_id=pid,
                ))

            db.session.commit()

            current_app.logger.info(
                f"webhooks.openemr | eid={eid} MeetingRecord recreated "
                f"old={old_meeting_id} new={meeting_data['meeting_id']}"
            )
            write_audit_log(
                event_type="meeting.recreated",
                success=True,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                zoom_meeting_id=meeting_data["meeting_id"],
            )

            if eid:
                success = write_zoom_urls_to_appointment(
                    eid=eid,
                    start_url=meeting_data["start_url"],
                    join_url=meeting_data["join_url"],
                )
                write_audit_log(
                    event_type="openemr.url_writeback_success" if success else "openemr.url_writeback_failed",
                    success=success,
                    zoom_account_id=account.account_id,
                    openemr_appointment_id=eid,
                    openemr_provider_id=mapping.openemr_provider_id,
                    openemr_patient_id=pid,
                    zoom_meeting_id=meeting_data["meeting_id"],
                    error_message=None if success else "Zoom URL writeback failed",
                )

            return {
                "account_id": account.account_id,
                "zoom_meeting_id": meeting_data["meeting_id"],
                "zoom_join_url": meeting_data["join_url"],
                "zoom_start_url": meeting_data["start_url"],
                "action": "recreated",
            }
        except Exception as e:
            db.session.rollback()
            write_audit_log(
                event_type="meeting.recreate_failed",
                success=False,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                openemr_provider_id=mapping.openemr_provider_id,
                openemr_patient_id=pid,
                zoom_meeting_id=meeting_data.get("meeting_id"),
                error_message=str(e),
                detail={"stage": "local_record_recreate"},
            )
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
            write_audit_log(
                event_type="meeting.update_failed",
                success=False,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                openemr_provider_id=mapping.openemr_provider_id,
                openemr_patient_id=payload_pid,
                zoom_meeting_id=record.zoom_meeting_id,
                error_message=str(e),
                detail={"stage": "zoom_update"},
            )
            return {"error": str(e)}

        try:
            record.openemr_appt_status = payload.get("appt_status")
            db.session.commit()

            current_app.logger.info(
                f"webhooks.openemr | eid={eid} MeetingRecord "
                f"zoom_meeting_id={record.zoom_meeting_id} updated"
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
                "action": "updated",
            }
        except Exception as e:
            db.session.rollback()
            write_audit_log(
                event_type="meeting.update_failed",
                success=False,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                openemr_provider_id=mapping.openemr_provider_id,
                openemr_patient_id=payload_pid,
                zoom_meeting_id=record.zoom_meeting_id,
                error_message=str(e),
                detail={"stage": "local_record_update"},
            )
            return {"error": str(e)}

# ---------------------------------------------------------------------------
# Delete handler
# ---------------------------------------------------------------------------
 
def _process_appointment_delete(payload: dict) -> tuple[dict, int]:
    """
    Handle appointment.deleted events from OpenEMR.

    Looks up MeetingRecord(s) by eid, deletes the Zoom meeting, and then
    either:
      - removes the local MeetingRecord (cascade cleans MeetingPatient rows)
        when no clinical note was ever received, or
      - preserves the MeetingRecord with status='cancelled' when a
        ClinicalNoteRecord exists. Per the system's design, any received note
        must be written back to the EHR, so an existing ClinicalNoteRecord
        represents real EHR work (or an anomalous state that needs
        investigation) — never silent cleanup.
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
        write_audit_log(
            event_type="appointment.delete_no_record",
            success=True,
            openemr_appointment_id=eid,
        )
        return {"status": "no_record", "eid": eid}, 200
 
    deleted_meetings = []
    errors = []
 
    for record in records:
        patient = MeetingPatient.query.filter_by(
            zoom_meeting_id=record.zoom_meeting_id
        ).first()
        patient_id = patient.openemr_patient_id if patient else None
        account = ZoomAccount.query.filter_by(
            account_id=record.zoom_account_id, is_active=True
        ).first()
        if not account:
            write_audit_log(
                event_type="meeting.delete_failed",
                success=False,
                zoom_account_id=record.zoom_account_id,
                openemr_appointment_id=eid,
                openemr_provider_id=record.openemr_provider_id,
                openemr_patient_id=patient_id,
                zoom_meeting_id=record.zoom_meeting_id,
                error_message="no active account found",
                detail={"stage": "account_lookup"},
            )
            errors.append({"meeting_id": record.zoom_meeting_id, "error": "no active account found"})
            continue

        meeting_id = record.zoom_meeting_id
 
        # Delete from Zoom
        try:
            delete_zoom_meeting(account, meeting_id)
        except Exception as e:
            current_app.logger.error(
                f"webhooks.openemr | eid={eid} failed to delete Zoom meeting "
                f"{meeting_id}: {e}"
            )
            write_audit_log(
                event_type="meeting.delete_failed",
                success=False,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                openemr_provider_id=record.openemr_provider_id,
                openemr_patient_id=patient_id,
                zoom_meeting_id=meeting_id,
                error_message=str(e),
                detail={"stage": "zoom_delete"},
            )
            errors.append({"meeting_id": meeting_id, "error": str(e)})
            # Mark record as error but continue — still remove from DB
            record.status = "error"
            db.session.commit()
            continue
 
        # Branch on whether any clinical note was ever received for this
        # meeting. If yes, preserve the row as an audit trail; if no, the
        # local record can be removed (cascade cleans MeetingPatient rows).
        try:
            if record.clinical_note is not None:
                record.status = "cancelled"
                db.session.commit()
                current_app.logger.info(
                    f"webhooks.openemr | eid={eid} MeetingRecord "
                    f"zoom_meeting_id={meeting_id} cancelled (clinical note preserved)"
                )
                write_audit_log(
                    event_type="meeting.cancelled",
                    success=True,
                    zoom_account_id=account.account_id,
                    openemr_appointment_id=eid,
                    openemr_provider_id=record.openemr_provider_id,
                    openemr_patient_id=patient_id,
                    zoom_meeting_id=meeting_id,
                    detail={"preserved": True, "reason": "clinical_note_present"},
                )
            else:
                db.session.delete(record)
                db.session.commit()
                current_app.logger.info(
                    f"webhooks.openemr | eid={eid} MeetingRecord zoom_meeting_id={meeting_id} deleted"
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
                f"zoom_meeting_id={meeting_id}: {e}"
            )
            write_audit_log(
                event_type="meeting.delete_failed",
                success=False,
                zoom_account_id=account.account_id,
                openemr_appointment_id=eid,
                openemr_provider_id=record.openemr_provider_id,
                openemr_patient_id=patient_id,
                zoom_meeting_id=meeting_id,
                error_message=str(e),
                detail={"stage": "local_record_delete"},
            )
            errors.append({"meeting_id": meeting_id, "error": str(e)})
 
    if errors and not deleted_meetings:
        return {"status": "error", "eid": eid, "errors": errors}, 500
 
    return {
        "status": "deleted",
        "eid": eid,
        "deleted_meetings": deleted_meetings
    }, 200

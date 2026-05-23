import logging
from datetime import date, datetime, time, timedelta

from sqlalchemy import text
from app.extensions import db, get_openemr_db_engine
from app.services.audit import write_audit_log


logger = logging.getLogger(__name__)


# OpenEMR-standard PHP-serialized blobs for the non-recurring / empty-location
# default shape — extracted from 04_appointment_types.sql so direct DB writes
# match what the OpenEMR UI would produce. Both columns are NOT NULL.
_RECURRSPEC_NONE = (
    'a:6:{s:17:"event_repeat_freq";s:1:"0";'
    's:22:"event_repeat_freq_type";s:1:"0";'
    's:19:"event_repeat_on_num";s:1:"1";'
    's:19:"event_repeat_on_day";s:1:"0";'
    's:20:"event_repeat_on_freq";s:1:"0";'
    's:6:"exdate";s:0:"";}'
)
_LOCATION_EMPTY = (
    'a:6:{s:14:"event_location";s:0:"";'
    's:13:"event_street1";s:0:"";'
    's:13:"event_street2";s:0:"";'
    's:10:"event_city";s:0:"";'
    's:11:"event_state";s:0:"";'
    's:12:"event_postal";s:0:"";}'
)


def get_appointment_types_list() -> list[dict]:
    """
    Query OpenEMR appointment categories directly from MariaDB.
    No API endpoint exists for this resource in OpenEMR 8.0.0.
    """
    engine = get_openemr_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT pc_catid, pc_catname, pc_catdesc, pc_duration, pc_catcolor
            FROM openemr_postcalendar_categories
            WHERE pc_active = 1
            ORDER BY pc_seq
        """))
        return [
            {
                "id": str(row.pc_catid),
                "name": row.pc_catname,
                "description": row.pc_catdesc,
                "duration_seconds": row.pc_duration,
                "color": row.pc_catcolor,
            }
            for row in result
        ]
    

def get_appointment_details(eid: int) -> dict | None:
    """Get appointment fields needed for encounter creation."""

    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    SELECT pc_pid, pc_aid, pc_facility, pc_catid
                    FROM openemr_postcalendar_events
                    WHERE pc_eid = :eid
                """),
                {"eid": int(eid)}
            )
            row = result.fetchone()
            if not row:
                return None
            return {
                "pid": row.pc_pid,
                "provider_id": row.pc_aid,
                "facility_id": row.pc_facility,
                "pc_catid": row.pc_catid,
            }
    except Exception as e:
        logger.error(f"openemr.get_appointment_details | Failed for eid={eid}: {e}")
        return None


def write_zoom_urls_to_appointment(
    eid: int,
    start_url: str,
    join_url: str
) -> bool:
    """
    Write Zoom meeting URLs back to the OpenEMR appointment record.

    Uses direct MariaDB connection — the FHIR Appointment resource
    is read-only in OpenEMR 8.0, so there is no API path for this write.

    Fields updated:
      pc_website  — currently written with the Zoom start URL
                    (intentional current behavior)

    Args:
        eid:       OpenEMR appointment ID (pc_eid)
        start_url: Zoom host start URL (provider/alternative host)
        join_url:  Zoom patient join URL (currently unused in writeback)

    Returns:
        True if the update affected a row, False if eid not found.
    """
    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE openemr_postcalendar_events
                    SET
                        pc_website = :website
                    WHERE pc_eid = :eid
                """),
                {
                    "website": start_url,
                    "eid": int(eid),
                }
            )

        if result.rowcount == 0:
            logger.warning(
                f"openemr.write_zoom_urls | No appointment found for eid={eid}"
            )
            return False

        logger.info(
            f"openemr.write_zoom_urls | Written Zoom URLs to appointment eid={eid}"
        )
        return True

    except Exception as e:
        logger.error(
            f"openemr.write_zoom_urls | Failed to write URLs for eid={eid}: {e}"
        )
        return False
    

def generate_future_appointment(
    *,
    zoom_account_id: str,
    provider_user_id: int,
    facility_id: int,
    patient_pid: int,
    category_id: int,
    category_name: str,
    slot_date: date,
    slot_time: time,
    duration_seconds: int = 1800,
    title: str | None = None,
    comment: str | None = None,
    status: str = "-",
) -> int | None:
    """
    Insert a single appointment into openemr_postcalendar_events mirroring the
    shape the OpenEMR UI / FHIR Appointment write would produce. Returns the
    new pc_eid.

    Used by the Sprint 13 hydration flow to materialize future appointments
    for mapped providers. Pure OpenEMR DB write — the orchestrator (S13-04)
    wires the result into the existing Zoom-meeting-creation path so the
    seeded appointment ends up with a real Zoom meeting + MeetingRecord.

    Defaults:
      duration_seconds=1800     30 min, matches the seed default
      title=category_name       falls through to the category label
      comment=""                empty (matches the seed convention)
      status='-'                Pending (the seed default before check-in)

    Audit:
      Emits `demo.future_appointment_created` on success and
      `demo.future_appointment_create_failed` on DB exception, both scoped
      to the supplied zoom_account_id so the hydration trail is reconstructable
      per-account.

    Returns:
        New pc_eid on success, None on failure (caller decides whether to
        skip or retry; logged + audited either way).
    """
    end_time = (
        datetime.combine(slot_date, slot_time) + timedelta(seconds=duration_seconds)
    ).time()

    audit_detail = {
        "category_id": int(category_id),
        "category_name": category_name,
        "slot_date": slot_date.isoformat(),
        "slot_time": slot_time.isoformat(),
        "duration_seconds": int(duration_seconds),
        "facility_id": int(facility_id),
    }

    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO openemr_postcalendar_events (
                        pc_catid, pc_multiple, pc_aid, pc_pid,
                        pc_title, pc_time, pc_hometext,
                        pc_eventDate, pc_endDate,
                        pc_duration, pc_recurrtype, pc_recurrfreq,
                        pc_recurrspec, pc_location,
                        pc_startTime, pc_endTime,
                        pc_alldayevent, pc_apptstatus, pc_eventstatus,
                        pc_sharing, pc_facility, pc_billing_location,
                        pc_informant, pc_sendalertsms, pc_sendalertemail,
                        uuid
                    ) VALUES (
                        :category_id, 0, :provider_id, :pid,
                        :title, NOW(), :comment,
                        :event_date, '0000-00-00',
                        :duration, 0, 0,
                        :recurrspec, :location,
                        :start_time, :end_time,
                        0, :status, 1,
                        1, :facility_id, :facility_id,
                        1, 'NO', 'NO',
                        UNHEX(REPLACE(UUID(), '-', ''))
                    )
                """),
                {
                    "category_id": int(category_id),
                    "provider_id": str(provider_user_id),
                    "pid":         str(patient_pid),
                    "title":       title or category_name,
                    "comment":     comment or "",
                    "event_date":  slot_date,
                    "duration":    int(duration_seconds),
                    "recurrspec":  _RECURRSPEC_NONE,
                    "location":    _LOCATION_EMPTY,
                    "start_time":  slot_time,
                    "end_time":    end_time,
                    "status":      status,
                    "facility_id": int(facility_id),
                },
            )
            eid = result.lastrowid
    except Exception as e:
        logger.error(
            f"openemr.generate_future_appointment | INSERT failed: "
            f"provider={provider_user_id} pid={patient_pid} date={slot_date}: {e}"
        )
        write_audit_log(
            event_type="demo.future_appointment_create_failed",
            success=False,
            zoom_account_id=zoom_account_id,
            openemr_provider_id=str(provider_user_id),
            openemr_patient_id=str(patient_pid),
            error_message=str(e),
            detail=audit_detail,
        )
        return None

    logger.info(
        f"openemr.generate_future_appointment | created eid={eid} "
        f"provider={provider_user_id} pid={patient_pid} "
        f"date={slot_date} time={slot_time} category={category_name}"
    )
    # Insert the matching patient_tracker row (encounter=0; will be updated
    # later by either OpenEMR's PHP path on status change or by our own
    # create_encounter helper).
    if eid:
        upsert_patient_tracker(
            eid=int(eid),
            pid=int(patient_pid),
            apptdate=slot_date,
            appttime=slot_time,
            encounter=0,
            original_user="zoomly_demo_hydrate",
        )
    write_audit_log(
        event_type="demo.future_appointment_created",
        success=True,
        zoom_account_id=zoom_account_id,
        openemr_appointment_id=str(eid) if eid else None,
        openemr_provider_id=str(provider_user_id),
        openemr_patient_id=str(patient_pid),
        detail=audit_detail,
    )
    return int(eid) if eid else None


def upsert_patient_tracker(
    *,
    eid: int,
    pid: int,
    apptdate: date,
    appttime: time,
    encounter: int = 0,
    original_user: str = "system",
) -> None:
    """
    Insert-or-update a patient_tracker row for the appointment.

    OpenEMR's PHP path (add_edit_event.php → manage_tracker_status) maintains
    patient_tracker.encounter as the canonical "this appointment's encounter"
    pointer that the Flow Board's Encounter column reads from. Direct DB
    inserts of openemr_postcalendar_events or form_encounter bypass that
    PHP path, so any Zoomly code that creates an appointment or encounter
    via raw SQL must call this helper to keep patient_tracker consistent.

    If a tracker row already exists for the (eid, pid) pair, only the
    `encounter` column is updated (and only when a non-zero value is
    supplied). If no row exists, one is inserted with the supplied values.
    Safe to call multiple times for the same appointment.
    """
    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            existing = conn.execute(
                text("SELECT id, encounter FROM patient_tracker WHERE eid = :eid AND pid = :pid LIMIT 1"),
                {"eid": int(eid), "pid": int(pid)},
            ).fetchone()
            if existing:
                if int(encounter) > 0 and int(encounter) != int(existing.encounter):
                    conn.execute(
                        text("UPDATE patient_tracker SET encounter = :enc WHERE id = :id"),
                        {"enc": int(encounter), "id": int(existing.id)},
                    )
                return
            conn.execute(
                text("""
                    INSERT INTO patient_tracker
                        (date, apptdate, appttime, eid, pid, original_user, encounter, lastseq, drug_screen_completed)
                    VALUES
                        (NOW(), :apptdate, :appttime, :eid, :pid, :user, :enc, '1', 0)
                """),
                {
                    "apptdate": apptdate,
                    "appttime": appttime,
                    "eid": int(eid),
                    "pid": int(pid),
                    "user": original_user,
                    "enc": int(encounter),
                },
            )
    except Exception as e:
        logger.error(
            f"openemr.upsert_patient_tracker | Failed for eid={eid} pid={pid}: {e}"
        )


def update_appointment_status(eid: int, status: str = "@") -> bool:
    """
    Update appointment status on openemr_postcalendar_events.
    
    Status codes:
      '@' = Arrived
      '-' = None
      '*' = Reminder done
      '+' = Chart pulled
      'x' = Canceled
      '?' = No show
    
    Args:
        eid:    OpenEMR appointment ID (pc_eid)
        status: Single character status code, default '@' (Arrived)
    
    Returns:
        True if row was updated, False if eid not found
    """

    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE openemr_postcalendar_events
                    SET pc_apptstatus = :status
                    WHERE pc_eid = :eid
                """),
                {"status": status, "eid": int(eid)}
            )
        if result.rowcount == 0:
            logger.warning(f"openemr.update_appointment_status | No appointment found for eid={eid}")
            return False
        logger.info(f"openemr.update_appointment_status | eid={eid} status updated to '{status}'")
        return True
    except Exception as e:
        logger.error(f"openemr.update_appointment_status | Failed for eid={eid}: {e}")
        return False


import logging
from sqlalchemy import text
from app.extensions import db, get_openemr_db_engine


logger = logging.getLogger(__name__)


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
    

# Update Appointment Status 
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


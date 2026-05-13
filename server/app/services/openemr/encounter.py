import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from app.extensions import get_openemr_db_engine


logger = logging.getLogger(__name__)


def find_encounter_for_appointment(eid: int, pid: int, provider_id: int) -> tuple[int | None, str | None]:
    """
    Find an existing encounter for a given appointment.

    Lookup order:
        1. external_id = 'zoom_eid_{eid}'  — already claimed by Zoomly
        2. Most recent encounter for pid + provider_id on today's date
           with no external_id — manually created via UI status change.
           If found, immediately stamps external_id to claim it.

    Args:
        eid:         OpenEMR appointment EID
        pid:         OpenEMR patient ID
        provider_id: OpenEMR provider users.id

    Returns:
        (encounter_number, source)
          encounter_number: int or None if no encounter found
          source:           "external_id"      — found via path 1
                            "manual_fallback"  — found via path 2 (S7-01 territory)
                            None               — not found
    """
    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            # --- 1. Check by external_id (fastest path) ---
            result = conn.execute(
                text("""
                    SELECT encounter FROM form_encounter
                    WHERE external_id = :external_id
                    LIMIT 1
                """),
                {"external_id": f"zoom_eid_{eid}"}
            ).fetchone()

            if result:
                logger.info(
                    f"openemr.find_encounter | Found by external_id zoom_eid_{eid} "
                    f"→ encounter={result.encounter}"
                )
                return result.encounter, "external_id"

            # --- 2. Fallback: manually created encounter (no external_id) ---
            # Provider manually set status to Arrived in OpenEMR UI,
            # triggering OpenEMR's auto-create which sets no external_id.
            # Stamp immediately so all future lookups hit path 1.
            result = conn.execute(
                text("""
                    SELECT encounter FROM form_encounter
                    WHERE pid = :pid
                    AND provider_id = :provider_id
                    AND DATE(date) = CURDATE()
                    AND (external_id IS NULL OR external_id = '')
                    ORDER BY encounter DESC
                    LIMIT 1
                """),
                {"pid": int(pid), "provider_id": int(provider_id)}
            ).fetchone()

            if result:
                # Claim — stamp external_id so future lookups find it via path 1
                conn.execute(
                    text("""
                        UPDATE form_encounter
                        SET external_id = :external_id
                        WHERE encounter = :encounter
                    """),
                    {
                        "external_id": f"zoom_eid_{eid}",
                        "encounter": result.encounter
                    }
                )
                logger.info(
                    f"openemr.find_encounter | Found manually-created encounter "
                    f"pid={pid} provider={provider_id} → encounter={result.encounter} "
                    f"— stamped external_id=zoom_eid_{eid}"
                )
                return result.encounter, "manual_fallback"

    except Exception as e:
        logger.error(f"openemr.find_encounter | Failed for eid={eid}: {e}")

    return None, None


def create_encounter(
    pid: int,
    provider_id: int,
    facility_id: int,
    pc_catid: int,
    eid: int,
    reason: str = "Zoom Telehealth Visit",
    class_code: str = "VR",
) -> int | None:
    """
    Create a new encounter in OpenEMR linked to a Zoom appointment.

    Replicates what OpenEMR's auto-create encounter does when appointment
    status is changed to Arrived via the UI.
    - changing via the direct DB connection does not trigger the auto-create function
    

    Uses the sequences table to get the next encounter number atomically.
    Sets external_id = 'zoom_eid_{eid}' for reliable lookup later.

    Args:
        pid:         OpenEMR patient ID
        provider_id: OpenEMR provider users.id
        facility_id: OpenEMR facility ID
        pc_catid:    Calendar category ID (appointment type)
        eid:         OpenEMR appointment EID (stored in external_id)
        reason:      Reason for visit text
        class_code:  HL7 encounter class — 'VR' for virtual

    Returns:
        encounter number (int) if successful, None on failure
    """

    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            # Check if encounter already exists for this eid
            existing = conn.execute(
                text("SELECT encounter FROM form_encounter WHERE external_id = :external_id"),
                {"external_id": f"zoom_eid_{eid}"}
            ).fetchone()

            if existing:
                logger.info(f"openemr.create_encounter | Encounter already exists for eid={eid}, skipping")
                return existing.encounter
            
            # --- 1. If not existing - Get next encounter number atomically ---
            conn.execute(text("UPDATE sequences SET id = id + 1"))
            result = conn.execute(text("SELECT id FROM sequences"))
            encounter_number = result.scalar()

            # --- 2. Insert form_encounter ---
            encounter_uuid = uuid.uuid4().bytes
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")

            conn.execute(
                text("""
                    INSERT INTO form_encounter (
                        uuid, date, pid, encounter,
                        pc_catid, provider_id, facility_id,
                        billing_facility, class_code,
                        reason, external_id,
                        sensitivity, in_collection
                    ) VALUES (
                        :uuid, :date, :pid, :encounter,
                        :pc_catid, :provider_id, :facility_id,
                        :billing_facility, :class_code,
                        :reason, :external_id,
                        '', 0
                    )
                """),
                {
                    "uuid": encounter_uuid,
                    "date": today,
                    "pid": int(pid),
                    "encounter": encounter_number,
                    "pc_catid": int(pc_catid),
                    "provider_id": int(provider_id),
                    "facility_id": int(facility_id),
                    "billing_facility": int(facility_id),
                    "class_code": class_code,
                    "reason": reason,
                    "external_id": f"zoom_eid_{eid}",
                }
            )
            # Look up provider username for forms.user field
            user_result = conn.execute(
                text("SELECT username FROM users WHERE id = :provider_id"),
                {"provider_id": int(provider_id)}
            )
            row = user_result.fetchone()
            provider_username = row.username if row else "admin"

            # --- 3. Insert forms table entry to link encounter form ---
            forms_result = conn.execute(
                text("""
                    INSERT INTO forms (
                        date, encounter, form_name, formdir,
                        pid, authorized, deleted, provider_id, user, groupname
                    ) VALUES (
                        :date, :encounter, :form_name, :formdir,
                        :pid, 1, 0, :provider_id, :user, 'Default'
                    )
                """),
                {
                    "date": now,
                    "encounter": encounter_number,
                    "form_name": "New Patient Encounter",
                    "formdir": "newpatient",
                    "pid": int(pid),
                    "provider_id": int(provider_id),
                    "user": provider_username
                }
            )
            # --- 4. Set form_id to self-referential id ---
            forms_id = forms_result.lastrowid
            conn.execute(
                text("UPDATE forms SET form_id = :form_id WHERE id = :id"),
                {"form_id": forms_id, "id": forms_id}
            )

        logger.info(
            f"openemr.create_encounter | Created encounter={encounter_number} "
            f"pid={pid} eid={eid} provider={provider_id}"
        )
        return encounter_number

    except Exception as e:
        logger.error(f"openemr.create_encounter | Failed for pid={pid} eid={eid}: {e}")
        return None


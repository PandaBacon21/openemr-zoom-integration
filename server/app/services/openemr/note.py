import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from app.extensions import get_openemr_db_engine


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SOAP section mapping
# ---------------------------------------------------------------------------
 
# Maps Zoom note section headers to SOAP fields.
# Keys are lowercase for case-insensitive matching.
SOAP_SECTION_MAP = {
    # Subjective
    "subjective":                       "subjective",
    "chief complaint":                  "subjective",
    "history of present illness":       "subjective",
    "hpi":                              "subjective",
    "review of systems":                "subjective",
    "ros":                              "subjective",
    "symptoms and stressors":           "subjective",
    "subjective narrative":             "subjective",
    "discussion notes":                 "subjective",
    "reason for visit":                 "subjective",
    "past medical history":             "subjective",
    "past psychiatric history":         "subjective",
    "past surgical history":            "subjective",
    "family history":                   "subjective",
    "social history":                   "subjective",
    "medications":                      "subjective",
    "allergies":                        "subjective",
    "immunizations":                    "subjective",
    "development history":              "subjective",
    "anticipatory guidance":            "subjective",
    "diet & nutrition":                 "subjective",
    "diet and nutrition":               "subjective",
 
    # Objective
    "objective":                        "objective",
    "physical exam":                    "objective",
    "vitals":                           "objective",
    "results":                          "objective",
    "mental status exam":               "objective",
    "functional status":                "objective",
    "procedures":                       "objective",
    "hospital / ed course":             "objective",
    "hospital course":                  "objective",
    "ed course":                        "objective",
    "response to therapy":              "objective",
 
    # Assessment
    "assessment":                       "assessment",
    "risk assessment":                  "assessment",
    "problem list":                     "assessment",
    "generated diagnoses & codes":      "assessment",
    "generated diagnoses and codes":    "assessment",
 
    # Plan
    "plan":                             "plan",
    "assessment & plan":                "plan",
    "assessment and plan":              "plan",
    "patient recommendations":          "plan",
    "goals narrative":                  "plan",
    "disposition":                      "plan",
    "advanced directives":              "plan",
}
 
 
def parse_soap_sections(note_content: str) -> dict:
    """
    Parse Zoom clinical note content into SOAP sections.
 
    The note_content is plain text with section headers followed by content.
    Section headers are lines that match known Zoom section names.
    Content continues until the next section header.
 
    Unrecognized sections default to 'subjective' as a catch-all.
 
    Args:
        note_content: Raw note_content string from Zoom clinical notes API
 
    Returns:
        dict with keys: subjective, objective, assessment, plan
        Each value is a string of accumulated content for that section.
    """
    sections = {"subjective": [], "objective": [], "assessment": [], "plan": []}
    current_field = "subjective"  # default catch-all
    current_header = None
    buffer = []
    headers_recognized = 0

    def flush_buffer():
        if buffer and current_header is not None:
            content = "\n".join(buffer).strip()
            if content:
                sections[current_field].append(f"{current_header}\n{content}")
        buffer.clear()

    for line in note_content.splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        # Check if this line is a known section header
        matched_field = SOAP_SECTION_MAP.get(lower)

        if matched_field is not None:
            # Flush previous section buffer
            flush_buffer()
            current_field = matched_field
            current_header = stripped
            headers_recognized += 1
        else:
            buffer.append(stripped)

    # Flush final buffer
    flush_buffer()

    result = {
        "subjective":  "\n\n".join(sections["subjective"]),
        "objective":   "\n\n".join(sections["objective"]),
        "assessment":  "\n\n".join(sections["assessment"]),
        "plan":        "\n\n".join(sections["plan"]),
    }
    logger.info(
        f"openemr.parse_soap | headers_recognized={headers_recognized} "
        f"subjective_chars={len(result['subjective'])} "
        f"objective_chars={len(result['objective'])} "
        f"assessment_chars={len(result['assessment'])} "
        f"plan_chars={len(result['plan'])}"
    )
    return result
 
def write_note_to_encounter(
    encounter_number: int,
    pid: int,
    provider_id: int,
    provider_username: str,
    note_content: str,
    note_title: str,
    note_id: str,
    note_writeback_mode: str = "both",
    ) -> bool:
    """
    Write Zoom clinical note into an OpenEMR encounter.
 
    Writes to two forms:
      1. form_soap           — parsed SOAP sections
      2. form_clinical_notes — full note content as narrative
 
    Both operations are idempotent:
      - Deduped by encounter + formdir via the forms registration table —
        at most one SOAP form and one Clinical Notes form per encounter.
 
    Args:
        encounter_number:  OpenEMR encounter number
        pid:               OpenEMR patient ID
        provider_id:       OpenEMR provider users.id
        provider_username: OpenEMR provider username (for forms.user field)
        note_content:      Raw note_content from Zoom clinical notes API
        note_title:        Note title from Zoom webhook payload
        note_id:           Zoom note ID (stored on form_clinical_notes.external_id
                           for traceability — refreshed on each write)
 
    Returns:
        True if successful, False on error
    """
    content_length = len(note_content) if note_content else 0
    stripped_length = len(note_content.strip()) if note_content else 0
    content_blank = stripped_length == 0
    logger.info(
        f"openemr.write_note_to_encounter | entry encounter={encounter_number} "
        f"note_id={note_id} mode={note_writeback_mode} "
        f"content_length={content_length} stripped_length={stripped_length} "
        f"content_blank={content_blank}"
    )

    engine = get_openemr_db_engine()
    now   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
 
    soap = parse_soap_sections(note_content)
 
    try:
        with engine.begin() as conn:
            if note_writeback_mode in ("both", "soap_only"):
                _upsert_soap_form(
                    conn=conn,
                    encounter_number=encounter_number,
                    pid=pid,
                    provider_id=provider_id,
                    provider_username=provider_username,
                    soap=soap,
                    now=now,
                )
            if note_writeback_mode in ("both", "clinical_note_only"):
                _upsert_clinical_note_form(
                    conn=conn,
                    encounter_number=encounter_number,
                    pid=pid,
                    provider_id=provider_id,
                    provider_username=provider_username,
                    note_content=note_content,
                    note_title=note_title,
                    note_id=note_id,
                    now=now,
                    today=today,
                )

        logger.info(
            f"openemr.write_note_to_encounter | mode={note_writeback_mode} "
            f"encounter={encounter_number} pid={pid} note_id={note_id}"
        )
        return True
 
    except Exception as e:
        logger.error(
            f"openemr.write_note_to_encounter | Failed for "
            f"encounter={encounter_number} pid={pid}: {e}"
        )
        return False


def _upsert_soap_form(
    conn,
    encounter_number: int,
    pid: int,
    provider_id: int,
    provider_username: str,
    soap: dict,
    now: str,
    ) -> int:
    """
    Insert or update a SOAP form for the given encounter.
 
    Dedup key: forms.encounter + forms.formdir = 'soap' + forms.deleted = 0
    On update: updates form_soap fields only — forms registration row already exists.
    On insert: inserts form_soap row and registers in forms table.
 
    Returns:
        soap_form_id (int) — the form_soap.id for the written row
    """
    existing = conn.execute(
        text("""
            SELECT form_id FROM forms
            WHERE encounter = :encounter
            AND formdir = 'soap'
            AND deleted = 0
            LIMIT 1
        """),
        {"encounter": encounter_number}
    ).fetchone()
 
    if existing:
        conn.execute(
            text("""
                UPDATE form_soap
                SET subjective = :subjective,
                    objective  = :objective,
                    assessment = :assessment,
                    plan       = :plan
                WHERE id = :id
            """),
            {
                "subjective": soap["subjective"],
                "objective":  soap["objective"],
                "assessment": soap["assessment"],
                "plan":       soap["plan"],
                "id":         existing.form_id,
            }
        )
        logger.info(
            f"openemr.write_note | soap | update encounter={encounter_number} "
            f"form_id={existing.form_id}"
        )
        return existing.form_id
 
    # No existing row — insert
    result = conn.execute(
        text("""
            INSERT INTO form_soap (
                date, pid, user, groupname,
                authorized, activity,
                subjective, objective, assessment, plan
            ) VALUES (
                :date, :pid, :user, 'Default',
                1, 1,
                :subjective, :objective, :assessment, :plan
            )
        """),
        {
            "date":        now,
            "pid":         int(pid),
            "user":        provider_username,
            "subjective":  soap["subjective"],
            "objective":   soap["objective"],
            "assessment":  soap["assessment"],
            "plan":        soap["plan"],
        }
    )
    soap_form_id = result.lastrowid
 
    # Register in forms table
    conn.execute(
        text("""
            INSERT INTO forms (
                date, encounter, form_name, formdir,
                pid, user, groupname, authorized,
                deleted, form_id, provider_id
            ) VALUES (
                :date, :encounter, 'SOAP', 'soap',
                :pid, :user, 'Default', 1,
                0, :form_id, :provider_id
            )
        """),
        {
            "date":        now,
            "encounter":   encounter_number,
            "pid":         int(pid),
            "user":        provider_username,
            "form_id":     soap_form_id,
            "provider_id": int(provider_id),
        }
    )

    logger.info(
        f"openemr.write_note | soap | insert encounter={encounter_number} "
        f"form_id={soap_form_id} pid={pid}"
    )
    return soap_form_id


def _upsert_clinical_note_form(
    conn,
    encounter_number: int,
    pid: int,
    provider_id: int,
    provider_username: str,
    note_content: str,
    note_title: str,
    note_id: str,
    now: str,
    today: str,
) -> int:
    """
    Insert or update a Clinical Notes form for the given encounter.

    Dedup key: forms.encounter + formdir='clinical_notes' + deleted=0
    (mirrors _upsert_soap_form — ensures one Clinical Notes form per encounter).

    external_id is still populated on insert and refreshed on update with the
    latest note_id so the row records which Zoom note last contributed to it.

    On update: refreshes description, external_id, and clinical_notes_type.
    On insert: inserts form_clinical_notes row (with self-referential form_id)
               and registers in forms table.

    Returns:
        cn_id (int) — the form_clinical_notes.id for the written row
    """
    existing = conn.execute(
        text("""
            SELECT form_id FROM forms
            WHERE encounter = :encounter
            AND formdir = 'clinical_notes'
            AND deleted = 0
            LIMIT 1
        """),
        {"encounter": encounter_number}
    ).fetchone()

    if existing:
        conn.execute(
            text("""
                UPDATE form_clinical_notes
                SET description = :description,
                    codetext    = '',
                    external_id = :external_id,
                    clinical_notes_type = 'general_note'
                WHERE id = :id
            """),
            {
                "description": f"{note_title}\n\n{note_content}",
                "external_id": note_id,
                "id":          existing.form_id,
            }
        )
        logger.info(
            f"openemr.write_note | clinical_notes | update id={existing.form_id} "
            f"external_id={note_id}"
        )
        return existing.form_id
 
    # No existing row — insert
    cn_uuid = uuid.uuid4().bytes
 
    result = conn.execute(
        text("""
            INSERT INTO form_clinical_notes (
                form_id, uuid, date, pid, encounter,
                user, groupname, authorized, activity,
                code, codetext, description, external_id,
                clinical_notes_type, clinical_notes_category
            ) VALUES (
                0, :uuid, :date, :pid, :encounter,
                :user, 'Default', 1, 1,
                '', '', :description, :external_id,
                'general_note', 'general'
            )
        """),
        {
            "uuid":        cn_uuid,
            "date":        today,
            "pid":         int(pid),
            "encounter":   str(encounter_number),
            "user":        provider_username,
            "description": f"{note_title}\n\n{note_content}",
            "external_id": note_id,
        }
    )

    cn_id = result.lastrowid
 
    # Self-referential form_id
    conn.execute(
        text("UPDATE form_clinical_notes SET form_id = :id WHERE id = :id"),
        {"id": cn_id}
    )
 
    # Register in forms table
    conn.execute(
        text("""
            INSERT INTO forms (
                date, encounter, form_name, formdir,
                pid, user, groupname, authorized,
                deleted, form_id, provider_id
            ) VALUES (
                :date, :encounter, 'Clinical Notes', 'clinical_notes',
                :pid, :user, 'Default', 1,
                0, :form_id, :provider_id
            )
        """),
        {
            "date":        now,
            "encounter":   encounter_number,
            "pid":         int(pid),
            "user":        provider_username,
            "form_id":     cn_id,
            "provider_id": int(provider_id),
        }
    )

    logger.info(
        f"openemr.write_note | clinical_notes | insert id={cn_id} "
        f"encounter={encounter_number} external_id={note_id}"
    )
    return cn_id
import logging
import jwt
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from flask import current_app, jsonify, request
from sqlalchemy import text
from app.services.ehr_context import _get_account_by_tenant, _verify_basic_auth, _verify_bearer_jwt
from app.blueprints.ehr_context import ehr_context_bp
from app.extensions import get_openemr_db_engine
from app.models import ProviderMapping, MeetingRecord


logger = logging.getLogger(__name__)


"""
Implements the two endpoints Zoom calls as part of the EHR integration flow:

  GET /rest/auth/gettoken
      Called by Zoom to obtain a short-lived JWT.
      Requires Basic Auth (username:password) and X-Tenant-ID header.
      Returns a JWT valid for 1 hour.

  POST /rest/openendpoint/service/getAppointments
      Called by Zoom with the JWT from gettoken.
      Returns appointments for the given Zoom user within ±2 hours of the
      requested dateTime.
      Zoom uses this to let the provider select the correct appointment,
      which is then saved into the clinical note's EHR context.
"""

@ehr_context_bp.route("/auth/gettoken", methods=["GET"])
def get_token():
    """
    Issue a short-lived JWT for Zoom's EHR integration auth flow.

    Zoom calls this endpoint first to obtain a token, then passes it
    as Authorization: Bearer <token> on subsequent API calls.

    Request:
        Header  Authorization:  Basic <base64(username:password)>
        Header  X-Tenant-ID:    <tenant_id>

    Response 200:
        {
            "access_token": "<jwt>",
            "token_type":   "Bearer",
            "expires_in":   3600
        }

    Response 401: missing/invalid credentials
    Response 404: unknown tenant
    Response 500: SECRET_KEY not configured on server
    """
    tenant_id = request.headers.get("X-Tenant-ID", "").strip()
    if not tenant_id:
        logger.warning("ehr_context.gettoken | Missing X-Tenant-ID header")
        return jsonify({"error": "Missing X-Tenant-ID header"}), 401

    account = _get_account_by_tenant(tenant_id)
    if not account:
        logger.warning(f"ehr_context.gettoken | No active account for tenant_id={tenant_id}")
        return jsonify({"error": "Unknown tenant"}), 404

    authorization = request.headers.get("Authorization", "")
    if not _verify_basic_auth(authorization, account):
        logger.warning(
            f"ehr_context.gettoken | Basic Auth failed for tenant_id={tenant_id}"
        )
        return jsonify({"error": "Invalid credentials"}), 401

    # Issue JWT
    now = datetime.now(timezone.utc)
    expires_in = 3600  # 1 hour

    secret = current_app.config.get("SECRET_KEY")
    if not secret: 
        logger.warning("ehr_context.verify_jwt | SECRET_KEY not configured on server")
        return jsonify({"error": "SECRET_KEY not configured on server"}), 500
        
    token = jwt.encode(
        {
            "sub": tenant_id,
            "tid": tenant_id,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        },
        secret,
        algorithm="HS256",
    )

    logger.info(f"ehr_context.gettoken | Issued token for tenant_id={tenant_id}")

    return jsonify({
        "token": token,
        "token_type":   "Bearer",
        "expires_in":   expires_in,
    }), 200


# ---------------------------------------------------------------------------
# POST /rest/openendpoint/service/getAppointments
# ---------------------------------------------------------------------------

@ehr_context_bp.route("/openendpoint/service/getAppointments", methods=["POST"])
def get_appointments():
    """
    Return appointments for a Zoom user within ±2 hours of the requested time.

    Zoom calls this after obtaining a token from /rest/auth/gettoken.
    The provider selects an appointment from the response, which Zoom saves
    into the clinical note's EHR context (appointment_id, provider_id, patient_id).

    Request:
        Header  Authorization:  Bearer <jwt>
        Header  X-Tenant-ID:    <tenant_id>
        Body    {
                    "dateTime":   "2026-04-27T15:00:00",  (UTC)
                    "zoomUserId": "abc123xyz"
                }

    Response 200:
        [
            {
                "appointmentId":   "391",
                "providerId":      "10",
                "patientId":       "109",
                "startTime":       "2026-04-27T15:00:00",  (UTC)
                "endTime":         "2026-04-27T15:30:00",  (UTC)
                "serviceType":     "Zoom Telehealth",
                "name":            "Aisha Johnson",
                "dob":             "1993-01-25",
                "gender":          "Female",
                "appointmentType": "Telehealth Zoom"
            },
            ...
        ]
    """
    # --- 1. Validate X-Tenant-ID ---
    tenant_id = request.headers.get("X-Tenant-ID", "").strip()
    if not tenant_id:
        logger.warning("ehr_context.getAppointments | Missing X-Tenant-ID header")
        return jsonify({"error": "Missing X-Tenant-ID header"}), 401

    account = _get_account_by_tenant(tenant_id)
    if not account:
        logger.warning(f"ehr_context.getAppointments | No active account for tenant_id={tenant_id}")
        return jsonify({"error": "Unknown tenant"}), 404

    # --- 2. Verify Bearer JWT ---
    authorization = request.headers.get("Authorization", "")
    if not _verify_bearer_jwt(authorization, tenant_id):
        logger.warning(
            f"ehr_context.getAppointments | JWT verification failed for tenant_id={tenant_id}"
        )
        return jsonify({"error": "Invalid or expired token"}), 401

    # --- 3. Parse request body ---
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON"}), 400

    date_time_str = body.get("dateTime")
    zoom_user_id  = body.get("zoomUserId")

    if not date_time_str or not zoom_user_id:
        return jsonify({"error": "Missing required fields: dateTime, zoomUserId"}), 400

    # Parse dateTime — Zoom sends UTC
    try:
        query_dt = datetime.fromisoformat(date_time_str)
    except ValueError:
        return jsonify({"error": f"Invalid dateTime format: {date_time_str}"}), 400

    # --- 4. Resolve zoomUserId → OpenEMR provider_id ---
    mappings = ProviderMapping.query.filter_by(
        zoom_account_id=account.account_id,
        zoom_user_id=zoom_user_id,
        is_active=True,
    ).all()

    if not mappings:
        return jsonify({"error": f"No provider mapping found for zoomUserId={zoom_user_id}"}), 404

    if len(mappings) == 1:
        chosen_mapping = mappings[0]
        provider_id = chosen_mapping.openemr_provider_id
    else:
        # Multiple providers share this Zoom user — find the active meeting
        mapped_provider_ids = [m.openemr_provider_id for m in mappings]

        active_record = MeetingRecord.query.filter(
            MeetingRecord.zoom_account_id == account.account_id,
            MeetingRecord.openemr_provider_id.in_(mapped_provider_ids),
            MeetingRecord.status == "started",
            MeetingRecord.meeting_started_at.isnot(None),
        ).order_by(MeetingRecord.meeting_started_at.desc()).first()

        if active_record:
            provider_id = active_record.openemr_provider_id
            logger.info(
                f"ehr_context.getAppointments | Multiple mappings resolved to "
                f"provider_id={provider_id} via meeting_id={active_record.zoom_meeting_id}"
            )
        else:
            provider_id = mappings[0].openemr_provider_id
            logger.warning(
                f"ehr_context.getAppointments | Multiple mappings for zoom_user_id={zoom_user_id} "
                f"but no started MeetingRecord found, falling back to provider_id={provider_id}"
            )
        chosen_mapping = next(
            (m for m in mappings if m.openemr_provider_id == provider_id),
            mappings[0],
        )

    # --- 5. Query appointments ±2 hours around query_dt ---
    # Zoom sends dateTime in UTC. OpenEMR stores times in local wall-clock,
    # so convert the UTC window into the *provider's* local timezone before
    # querying. Per-provider TZ from the mapped Zoom user profile wins;
    # account-level AccountConfig.timezone is the fallback (legacy mappings
    # with no zoom_user_timezone cached, or Zoom users without a profile TZ).
    provider_tz_str = chosen_mapping.zoom_user_timezone if chosen_mapping else None
    fallback_tz_str = (
        account.config.timezone if hasattr(account, 'config') and account.config
        else "America/New_York"  # matches AccountConfig.timezone default
    )
    tz_str = provider_tz_str or fallback_tz_str
    account_tz = ZoneInfo(tz_str)
    query_dt_local = query_dt.replace(tzinfo=timezone.utc).astimezone(account_tz).replace(tzinfo=None)
    window_start = query_dt_local - timedelta(hours=2)
    window_end   = query_dt_local + timedelta(hours=2)
    logger.info(
        f"ehr_context.getAppointments | "
        f"query_dt={query_dt} "
        f"tz={tz_str} (provider_tz={provider_tz_str or 'none'}, account_tz={fallback_tz_str}) "
        f"query_dt_local={query_dt_local} "
        f"window={window_start} to {window_end}"
    )

    # Build datetime strings for MariaDB comparison
    # pc_eventDate is DATE, pc_startTime is TIME — combine for comparison
    window_start_date = window_start.strftime("%Y-%m-%d")
    window_end_date   = window_end.strftime("%Y-%m-%d")
    window_start_time = window_start.strftime("%H:%M:%S")
    window_end_time   = window_end.strftime("%H:%M:%S")

    engine = get_openemr_db_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT
                        e.pc_eid,
                        e.pc_pid,
                        e.pc_aid,
                        e.pc_eventDate,
                        e.pc_startTime,
                        e.pc_endTime,
                        e.pc_title,
                        e.pc_duration,
                        c.pc_catname,
                        p.fname,
                        p.lname,
                        p.DOB,
                        p.sex
                    FROM openemr_postcalendar_events e
                    JOIN openemr_postcalendar_categories c
                        ON e.pc_catid = c.pc_catid
                    LEFT JOIN patient_data p
                        ON e.pc_pid = p.pid
                    WHERE e.pc_aid = :provider_id
                    AND e.pc_alldayevent = 0
                    AND (
                        (e.pc_eventDate = :start_date AND e.pc_startTime >= :start_time)
                        OR (e.pc_eventDate > :start_date AND e.pc_eventDate < :end_date)
                        OR (e.pc_eventDate = :end_date AND e.pc_startTime <= :end_time)
                    )
                    ORDER BY e.pc_eventDate, e.pc_startTime
                """),
                {
                    "provider_id": int(provider_id),
                    "start_date":  window_start_date,
                    "start_time":  window_start_time,
                    "end_date":    window_end_date,
                    "end_time":    window_end_time,
                }
            ).fetchall()
    except Exception as e:
        logger.error(f"ehr_context.getAppointments | DB error for provider_id={provider_id}: {e}")
        return jsonify({"error": "Database error querying appointments"}), 500

    # --- 6. Build response ---
    # Times stored in local (account) time — convert to UTC for response
    appointments = []
    for row in rows:
        # Build start datetime — pc_startTime comes back as timedelta from PyMySQL
        try:
            if isinstance(row.pc_startTime, timedelta):
                total_seconds = int(row.pc_startTime.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                start_dt = datetime(
                    row.pc_eventDate.year,
                    row.pc_eventDate.month,
                    row.pc_eventDate.day,
                    hours, minutes, seconds,
                    tzinfo=account_tz
                ).astimezone(timezone.utc).replace(tzinfo=None)
            else:
                start_dt = datetime.combine(
                    row.pc_eventDate, row.pc_startTime
                ).replace(tzinfo=account_tz).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            start_dt = None

        # Build end time from start + duration (seconds)
        try:
            end_dt = start_dt + timedelta(seconds=int(row.pc_duration)) if start_dt else None
        except Exception:
            end_dt = None
        
        appointments.append({
            "appointmentId":   str(row.pc_eid),
            "providerId":      str(row.pc_aid),
            "patientId":       str(row.pc_pid),
            "startTime":       start_dt.isoformat() + "Z" if start_dt else None,
            "endTime":         end_dt.isoformat()+ "Z" if end_dt else None,
            # "serviceType":     row.pc_title or "",
            "serviceType":     row.pc_catname or "",
            "name":            f"{row.fname or ''} {row.lname or ''}".strip(),
            "dob":             row.DOB.isoformat() if row.DOB else None,
            "gender":          row.sex or "",
            # "appointmentType": row.pc_catname or "",
            "appointmentType": row.pc_title or "", # swapped pc_title and pc_catname because Zoom uses 'appointmentType' to display in appointment picker 
        })
    logger.info(
        f"ehr_context.getAppointments | Returning {len(appointments)} appointments "
        f"for provider_id={provider_id} zoom_user_id={zoom_user_id} "
        f"window={window_start.isoformat()} to {window_end.isoformat()}"
    )

    response = {
        "status": 200, 
        "response": appointments
    }

    return jsonify(response), 200
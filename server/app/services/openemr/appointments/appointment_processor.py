import logging
from dataclasses import dataclass
from app.models import ZoomAccount, UserMapping, AppointmentTypeFilter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data transfer object
# ---------------------------------------------------------------------------

@dataclass
class AppointmentMatch:
    """
    Represents a confirmed match between an inbound appointment event
    and a registered Zoom account + provider mapping.

    Passed downstream to the Zoom meeting creation step (S4-04).
    """
    zoom_account: ZoomAccount
    provider_mapping: UserMapping
    payload: dict


# ---------------------------------------------------------------------------
# Filter logic
# ---------------------------------------------------------------------------

def filter_appointment_event(payload: dict) -> tuple[list[AppointmentMatch], str | None]:
    """
    Determine which registered Zoom accounts (if any) should receive a
    Zoom meeting for this appointment event.

    An appointment passes the filter for a given account when ALL of:
      1. provider_id resolves to a known NPI in OpenEMR's users table
      2. That NPI has an active UserMapping for the account
      3. The appointment's category_id is in the account's *Epic* AppointmentTypeFilter
         list (rows with integration != 'veradigm')

    Appointment types configured as Veradigm (integration='veradigm') are for the
    external Veradigm appointment page only. They are hard-dropped here (reason
    "veradigm_excluded") so they never create a Zoom meeting / MeetingRecord and
    therefore never enter the clinical-note writeback pipeline — regardless of the
    Epic allowlist state.

    If the *Epic* filter list for an account is empty, ALL non-Veradigm appointment
    types pass for that account. This avoids locking out accounts that haven't
    configured filters yet — consistent with an allowlist that defaults open.

    Args:
        payload: Validated appointment event dict from the webhook endpoint.
                 Expected keys: provider_id, category_id, eid, pid, etc.

    Returns:
        (matches, drop_reason)
          matches:     List of AppointmentMatch objects (may be empty)
          drop_reason: None when matches is non-empty.
                       Otherwise one of: "missing_provider_id",
                       "provider_unmapped", "account_inactive",
                       "veradigm_excluded", "type_mismatch".
    """
    provider_id = payload.get("provider_id")
    category_id = payload.get("category_id")
    eid = payload.get("eid")

    # --- 1. Resolve provider_id → UserMapping ---
    if not provider_id:
        logger.info(
            f"appointment_processor | eid={eid} has no provider_id, dropping"
        )
        return [], "missing_provider_id"

    # --- 2. Find all active UserMappings for this NPI ---
    # A single NPI could theoretically be mapped across multiple Zoom accounts
    # (e.g. a multi-tenant demo). We handle all of them.
    mappings = (
        UserMapping.query
        .filter_by(openemr_user_id=str(provider_id), is_active=True)
        .all()
    )

    if not mappings:
        logger.info(
            f"appointment_processor | eid={eid} provider_id={provider_id} "
            "has no active provider mappings, dropping"
        )
        return [], "provider_unmapped"

    # --- 3. For each mapping, check appointment type filter ---
    matches: list[AppointmentMatch] = []
    any_account_active = False
    any_type_mismatched = False
    any_veradigm_excluded = False

    category_id_str = str(category_id) if category_id is not None else None

    for mapping in mappings:
        account = ZoomAccount.query.filter_by(
            account_id=mapping.zoom_account_id, is_active=True
        ).first()

        if not account:
            logger.warning(
                f"appointment_processor | eid={eid} UserMapping id={mapping.id} "
                f"references inactive or missing ZoomAccount account_id={mapping.zoom_account_id}, skipping"
            )
            continue

        any_account_active = True

        # Fetch this account's appointment type filter list
        type_filters = (
            AppointmentTypeFilter.query
            .filter_by(zoom_account_id=account.account_id)
            .all()
        )

        # Split by integration. Veradigm-typed appointments are for the external
        # Veradigm appointment page only — hard-drop them so they never enter the
        # Epic Zoom-meeting / note-writeback pipeline. NULL/legacy rows count as
        # Epic. category_id/filter IDs are compared as strings (openemr_type_id is
        # varchar; payload category_id is an int).
        veradigm_type_ids = {
            f.openemr_type_id for f in type_filters if f.integration == "veradigm"
        }
        epic_type_filters = [
            f for f in type_filters if f.integration != "veradigm"
        ]

        if category_id_str is not None and category_id_str in veradigm_type_ids:
            any_veradigm_excluded = True
            logger.info(
                f"appointment_processor | eid={eid} account={account.account_id} "
                f"category_id={category_id} is a Veradigm type, excluded from the "
                "Epic pipeline"
            )
            continue

        if not epic_type_filters:
            # No Epic filters configured → all non-Veradigm types pass for this account
            logger.debug(
                f"appointment_processor | eid={eid} account={account.account_id} "
                "has no Epic type filters configured, passing all non-Veradigm types"
            )
            matches.append(AppointmentMatch(
                zoom_account=account,
                provider_mapping=mapping,
                payload=payload
            ))
            continue

        # Epic filters exist — check if this appointment's category is in the list
        allowed_type_ids = {f.openemr_type_id for f in epic_type_filters}

        if category_id_str in allowed_type_ids:
            logger.debug(
                f"appointment_processor | eid={eid} account={account.account_id} "
                f"category_id={category_id} matched filter, passing"
            )
            matches.append(AppointmentMatch(
                zoom_account=account,
                provider_mapping=mapping,
                payload=payload
            ))
        else:
            any_type_mismatched = True
            logger.info(
                f"appointment_processor | eid={eid} account={account.account_id} "
                f"category_id={category_id} not in filter list {allowed_type_ids}, dropping"
            )

    if matches:
        return matches, None

    if not any_account_active:
        return [], "account_inactive"

    if any_veradigm_excluded:
        return [], "veradigm_excluded"

    if any_type_mismatched:
        return [], "type_mismatch"

    return [], "unknown"
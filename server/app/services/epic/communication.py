"""ReceiveCommunication3 business logic for Epic-ZCC CTI screen pops."""

import logging
from dataclasses import dataclass

from app.models import UserMapping
from app.services.audit import write_audit_log
from app.services.epic.lookup_cache import get_cached_lookup
from app.services.epic.patient_search import _phone_digits, search_patients
from app.services.epic.screenpop_dispatch import dispatch


logger = logging.getLogger(__name__)


@dataclass
class ReceiveCommunicationResult:
    pushed: bool
    reason: str | None = None
    openemr_user_id: str | None = None
    openemr_patient_id: str | None = None
    subscriber_count: int = 0
    event: dict | None = None


def process_receive_communication(account, payload: dict) -> ReceiveCommunicationResult:
    """Resolve a ReceiveCommunication3 payload and dispatch a screen-pop event.

    Business misses are deliberately non-fatal: ZCC should not retry a call
    that is already connected just because Zoomly could not drive OpenEMR
    navigation. Every miss is audited with an explicit detail.reason.
    """
    recipient_id = payload["recipient_id"]
    try:
        mapping = UserMapping.query.filter_by(
            zoom_account_id=account.account_id,
            zcc_user_id=recipient_id,
            is_zcc_agent=True,
            is_active=True,
        ).first()
    except Exception as e:
        logger.error(
            "epic.receive_communication | mapping lookup failed "
            f"account_id={account.account_id} recipient_id={recipient_id}: {e}",
            exc_info=True,
        )
        return _failed(account.account_id, recipient_id, "db_error", error_message=str(e))

    if not mapping:
        return _failed(account.account_id, recipient_id, "unknown_agent")

    openemr_user_id = str(mapping.openemr_user_id) if mapping.openemr_user_id else None
    if not openemr_user_id:
        return _failed(
            account.account_id,
            recipient_id,
            "mapping_missing_openemr_user",
            openemr_user_id=None,
        )

    patient_id = (payload.get("patient_id") or "").strip()
    patient_id_type = (payload.get("patient_id_type") or "").strip()

    # ZCC puts the patient's phone in CallerPhoneNumber for both in- and outbound.
    # For outbound click-to-dial, CallerPhoneNumber is the number the agent dialed
    # (i.e. the patient's phone), while DialedPhoneNumber is the ZCC agent-side number.
    caller_phone_raw = payload.get("caller_number") or payload.get("dialed_number")
    normalized_caller_phone = _phone_digits(caller_phone_raw) if caller_phone_raw else None

    row = None
    cached = get_cached_lookup(account.account_id, normalized_caller_phone or "")
    if cached is not None:
        cached_rows = cached.get("rows") or []
        if len(cached_rows) == 1:
            # Unambiguous PatientLookUp result — no discriminator needed.
            # ZCC's patient_id_type in RC3 is the highest-priority IVR field it
            # echoes back, not a discriminator when only one candidate exists.
            row = cached_rows[0]
        elif len(cached_rows) > 1:
            # Multiple candidates — use RC3's identifier to pick one.
            if not patient_id:
                return _failed(
                    account.account_id,
                    recipient_id,
                    "missing_patient_id",
                    openemr_user_id=openemr_user_id,
                )
            row = _find_cached_patient(cached_rows, patient_id, patient_id_type)
            if row is None:
                return _failed(
                    account.account_id,
                    recipient_id,
                    "patient_not_in_cache",
                    openemr_user_id=openemr_user_id,
                    detail={
                        "patient_id_type": patient_id_type or None,
                        "cached_count": len(cached_rows),
                    },
                )
        # else 0 rows: PatientLookUp found nothing; fall through to direct search.

    if row is None:
        # No cache (or cache had 0 results) — build criteria from RC3 payload directly.
        # Priority: direct identifiers (DOB, SSN, MRN, FHIR) from LookupInformation
        # or LookupID. Phone (CallerPhoneNumber) is the fallback when no typed
        # identifier is present.
        criteria, search_type, fallback_phone = _build_rc3_criteria(
            patient_id, patient_id_type, payload
        )

        if not criteria:
            return _failed(
                account.account_id,
                recipient_id,
                "no_lookup_criteria",
                openemr_user_id=openemr_user_id,
                detail={"call_id": payload.get("call_id")},
            )

        try:
            rows, _ = search_patients(criteria)
        except Exception as e:
            logger.error(
                "epic.receive_communication | patient search failed "
                f"account_id={account.account_id} search_type={search_type!r}: {e}",
                exc_info=True,
            )
            return _failed(
                account.account_id,
                recipient_id,
                "search_error",
                openemr_user_id=openemr_user_id,
                error_message=str(e),
            )

        if len(rows) != 1:
            suffix = "ambiguous" if rows else "no_match"
            matched_on = f"{search_type}_{suffix}"
            finder_event = {
                "type": "navigate",
                "caller_number": fallback_phone,
                "matched_on": matched_on,
            }
            subscriber_count = dispatch(account.account_id, openemr_user_id, finder_event)
            write_audit_log(
                event_type="epic_zcc.receive_communication_pushed",
                success=True,
                zoom_account_id=account.account_id,
                openemr_user_id=openemr_user_id,
                detail={
                    "recipient_id": recipient_id,
                    "subscriber_count": subscriber_count,
                    "matched_on": matched_on,
                    "match_count": len(rows),
                    "search_type": search_type,
                    "call_id": payload.get("call_id"),
                },
            )
            return ReceiveCommunicationResult(
                pushed=True,
                openemr_user_id=openemr_user_id,
                subscriber_count=subscriber_count,
                event=finder_event,
            )

        row = rows[0]

    event = {
        "type": "navigate",
        "openemr_patient_id": str(row["pid"]),
        "matched_on": _matched_on(row, patient_id_type),
        "caller_number": payload.get("caller_number"),
    }
    subscriber_count = dispatch(account.account_id, openemr_user_id, event)
    if subscriber_count < 1:
        return _failed(
            account.account_id,
            recipient_id,
            "no_subscribers",
            openemr_user_id=openemr_user_id,
            openemr_patient_id=str(row["pid"]),
        )

    write_audit_log(
        event_type="epic_zcc.receive_communication_pushed",
        success=True,
        zoom_account_id=account.account_id,
        openemr_user_id=openemr_user_id,
        openemr_patient_id=str(row["pid"]),
        detail={
            "recipient_id": recipient_id,
            "subscriber_count": subscriber_count,
            "matched_on": event["matched_on"],
            "call_id": payload.get("call_id"),
        },
    )
    return ReceiveCommunicationResult(
        pushed=True,
        openemr_user_id=openemr_user_id,
        openemr_patient_id=str(row["pid"]),
        subscriber_count=subscriber_count,
        event=event,
    )


def _failed(
    account_id: str,
    recipient_id: str,
    reason: str,
    *,
    openemr_user_id: str | None = None,
    openemr_patient_id: str | None = None,
    detail: dict | None = None,
    error_message: str | None = None,
) -> ReceiveCommunicationResult:
    audit_detail = {"reason": reason, "recipient_id": recipient_id}
    if detail:
        audit_detail.update(detail)
    write_audit_log(
        event_type="epic_zcc.receive_communication_failed",
        success=False,
        zoom_account_id=account_id,
        openemr_user_id=openemr_user_id,
        openemr_patient_id=openemr_patient_id,
        detail=audit_detail,
        error_message=error_message or reason,
    )
    return ReceiveCommunicationResult(
        pushed=False,
        reason=reason,
        openemr_user_id=openemr_user_id,
        openemr_patient_id=openemr_patient_id,
    )


def _find_cached_patient(rows: list[dict], patient_id: str, patient_id_type: str | None) -> dict | None:
    for row in rows:
        if _patient_id_matches(row, patient_id, patient_id_type):
            return row
    return None


def _patient_id_matches(row: dict, patient_id: str, patient_id_type: str | None) -> bool:
    normalized_type = (patient_id_type or "").upper()
    value = patient_id.strip()
    value_lower = value.lower()

    if normalized_type in {"PH", "PHONE"}:
        digits = _phone_digits(value)
        return (
            _phone_digits(row.get("phone_cell") or "") == digits
            or _phone_digits(row.get("phone_home") or "") == digits
        )
    if normalized_type == "DOB":
        row_dob = row.get("DOB")
        row_dob_str = row_dob.isoformat() if (row_dob and hasattr(row_dob, "isoformat")) else str(row_dob or "")
        return row_dob_str == value
    if normalized_type in {"SS", "SSN"}:
        row_ssn4 = row.get("ssn_last4") or ""
        return row_ssn4 == value[-4:] if len(value) >= 4 else False
    if normalized_type in {"MRN", "EPI", "EPIID"}:
        return str(row.get("pubpid") or "") == value
    if normalized_type in {"FHIR", "FHIRID", "FHIR ID"}:
        return str(row.get("uuid_hex") or "").lower() == value_lower
    if normalized_type in {"INTERNAL", "PID", "OPENEMR"}:
        return str(row.get("pid") or "") == value

    return value in {
        str(row.get("pid") or ""),
        str(row.get("pubpid") or ""),
    } or value_lower == str(row.get("uuid_hex") or "").lower()


def _build_rc3_criteria(
    patient_id: str,
    patient_id_type: str,
    payload: dict,
) -> tuple[dict, str, str | None]:
    """Build search_patients criteria from ReceiveCommunication3 identifiers.

    Returns (criteria, search_type, fallback_phone).
    search_type labels the primary criterion used (drives matched_on strings).
    fallback_phone is CallerPhoneNumber (the patient's phone in both in- and outbound)
    for pre-filling the patient finder when the search yields no unique match.
    """
    fallback_phone = payload.get("caller_number") or payload.get("dialed_number")

    normalized_type = (patient_id_type or "").upper()
    if patient_id:
        if normalized_type == "DOB":
            return {"dob": patient_id}, "dob", fallback_phone
        if normalized_type in {"SS", "SSN"}:
            digits = "".join(c for c in patient_id if c.isdigit())
            if len(digits) >= 4:
                return {"ssn_last4": digits[-4:]}, "ssn", fallback_phone
        if normalized_type in {"MRN", "EPI", "EPIID"}:
            return {"patient_id": patient_id, "patient_id_type": "MRN"}, "mrn", fallback_phone
        if normalized_type in {"FHIR", "FHIRID", "FHIR ID"}:
            return {"patient_id": patient_id, "patient_id_type": "FHIR"}, "fhir", fallback_phone
        if normalized_type in {"PH", "PHONE"}:
            return {"phones": [patient_id]}, "phone", fallback_phone

    if fallback_phone:
        return {"phones": [fallback_phone]}, "phone", fallback_phone

    return {}, "unknown", None


def _matched_on(row: dict, patient_id_type: str | None) -> str:
    matched_fields = row.get("_matched_on") or []
    if matched_fields:
        return str(matched_fields[0])

    normalized_type = (patient_id_type or "").upper()
    if normalized_type in {"MRN", "EPI", "EPIID"}:
        return "mrn"
    if normalized_type in {"FHIR", "FHIRID", "FHIR ID"}:
        return "fhir"
    if normalized_type in {"INTERNAL", "PID", "OPENEMR"}:
        return "internal"
    return "patient_id"

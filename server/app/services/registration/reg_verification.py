import logging
import requests
from app.auth.jwt_assertion import get_openemr_token
from app.services.audit import write_audit_log


logger = logging.getLogger(__name__)


def verify_openemr_token_for_account(zoom_account) -> bool:
    """
    Confirm an OpenEMR access token can be fetched for a single account.

    Used by `POST /config/register/<id>/verify` as a status check.
    Returns True if a token was successfully fetched (cached or freshly minted)
    and stored, False otherwise. Does not raise — errors are caught and logged
    so the verify endpoint can keep returning a useful response shape.

    OpenEMR clients are auto-enabled at registration time
    (see `_enable_openemr_client` in registration.py), so 401/403 here means
    the client was *manually disabled* after registration, not "not yet
    enabled" as before.
    """
    try:
        get_openemr_token(zoom_account)
        logger.info(
            f"OpenEMR token verified for account {zoom_account.account_id}"
        )
        write_audit_log(
            event_type="openemr.token_verify_success",
            success=True,
            zoom_account_id=zoom_account.account_id,
        )
        return True
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        logger.warning(
            f"OpenEMR token verify failed for account {zoom_account.account_id} "
            f"(HTTP {status}): {e}"
        )
        write_audit_log(
            event_type="openemr.token_verify_failed",
            success=False,
            zoom_account_id=zoom_account.account_id,
            error_message=str(e),
            detail={"status_code": status if isinstance(status, int) else None},
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error verifying OpenEMR token for "
            f"account {zoom_account.account_id}: {e}"
        )
        write_audit_log(
            event_type="openemr.token_verify_failed",
            success=False,
            zoom_account_id=zoom_account.account_id,
            error_message=str(e),
            detail={"stage": "unexpected"},
        )
        return False
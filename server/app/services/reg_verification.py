import logging
from datetime import datetime, timezone, timedelta
import requests
from app.auth.jwt_assertion import get_openemr_token
from app.extensions import scheduler
from app.extensions import db

logger = logging.getLogger(__name__)


def verify_openemr_token_for_account(zoom_account) -> bool:
    """
    Attempt to fetch an OpenEMR access token for a single account.

    Called when:
      - The background scheduler checks pending accounts
      - The user manually triggers verification from the UI
      - An API call needs a token and none is cached

    Returns True if token was successfully fetched and stored, False otherwise.
    Does not raise — all errors are caught and logged so the scheduler
    can continue to the next account.
    """
    try:
        token = get_openemr_token(zoom_account, force_refresh=True)
        logger.info(
            f"OpenEMR token verified for account {zoom_account.account_id}"
        )
        return True
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        if status in (401, 403):
            # Client not yet enabled in OpenEMR — expected state, not an error
            logger.debug(
                f"Account {zoom_account.account_id} not yet enabled in OpenEMR "
                f"(HTTP {status}) — will retry"
            )
        else:
            logger.warning(
                f"Unexpected HTTP error verifying OpenEMR token for "
                f"account {zoom_account.account_id}: {e}"
            )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error verifying OpenEMR token for "
            f"account {zoom_account.account_id}: {e}"
        )
        return False


def check_pending_registrations(app) -> None:
    """
    Background job — triggered when a new registration occurs.
    Retries every 5 minutes until no pending accounts remain,
    then stops scheduling itself.
    """
    with app.app_context():
        from app.models import ZoomAccount
        from app.extensions import scheduler

        now = datetime.now(timezone.utc)

        pending = ZoomAccount.query.filter(
            ZoomAccount.is_active == True,
            db.or_(
                ZoomAccount.openemr_access_token == None,
                ZoomAccount.openemr_token_expires_at == None,
                ZoomAccount.openemr_token_expires_at <= now
            )
        ).all()

        if not pending:
            logger.info("No pending OpenEMR registrations — stopping verification scheduler")
            return

        logger.info(f"Checking {len(pending)} pending OpenEMR registration(s)")
        for account in pending:
            verify_openemr_token_for_account(account)

        # Check if any are still pending after verification attempts
        still_pending = ZoomAccount.query.filter(
            ZoomAccount.is_active == True,
            db.or_(
                ZoomAccount.openemr_access_token == None,
                ZoomAccount.openemr_token_expires_at == None,
                ZoomAccount.openemr_token_expires_at <= now
            )
        ).all()

        if still_pending:
            # Reschedule itself for another check in 5 minutes
            scheduler.add_job(
                func=check_pending_registrations,
                args=[app],
                trigger="date",
                run_date=datetime.now(timezone.utc) + timedelta(minutes=5),
                id="check_pending_registrations",
                replace_existing=True
            )
            logger.info(
                f"{len(still_pending)} account(s) still pending — "
                "rescheduled verification in 5 minutes"
            )
        else:
            logger.info("All accounts verified — verification scheduler stopped")

def trigger_verification_scheduler(app) -> None:
    """
    Schedule an immediate verification check.
    Called after a new registration to kick off the polling loop.
    Only schedules if not already running to avoid duplicate jobs.
    """


    scheduler.add_job(
        func=check_pending_registrations,
        args=[app],
        trigger="date",
        run_date=datetime.now(timezone.utc),
        id="check_pending_registrations",
        replace_existing=True  # safe to call multiple times
    )
    app.logger.info("Verification scheduler triggered")
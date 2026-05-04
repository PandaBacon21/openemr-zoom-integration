import logging
import requests
from flask import current_app
from .reg_verification import trigger_verification_scheduler
from app.extensions import db
from app.models import ZoomAccount, ZoomAccount, AccountConfig
from app.services.zoom import validate_zoom_credentials
from app.services.keys import generate_keypair, delete_keypair
from app.services.ehr_context import set_ehr_context_credentials, _generate_tenant_id


logger = logging.getLogger(__name__)


def _retrieve_scopes() -> list[str]: 
    return current_app.config["OPENEMR_SCOPES"]

def _register_with_openemr(
    zoom_account_id: str,
    contact_email: str
) -> dict:
    """
    Register this Zoom account as a SMART Backend Services client in OpenEMR.

    Uses OpenEMR's dynamic client registration endpoint (RFC 7591).
    The jwks_uri points to our JWKS endpoint which serves all active public keys.
    OpenEMR will fetch the JWKS, find the key matching kid, and use it to
    verify JWT assertions during token requests.

    Returns the full registration response dict from OpenEMR.
    Raises: requests.HTTPError if registration fails.
    """
    openemr_base_url = current_app.config["OPENEMR_BASE_URL"]
    app_internal_url = current_app.config.get("APP_INTERNAL_URL", "http://zoom-bridge:5000")

    registration_endpoint = f"{openemr_base_url}/oauth2/default/registration"
    jwks_uri = f"{app_internal_url}/.well-known/jwks.json"

    payload = {
        "application_type": "private",
        "client_name": f"Zoomly Bridge - {zoom_account_id}",
        "contacts": [contact_email],
        "token_endpoint_auth_method": "private_key_jwt",
        "scope": " ".join(_retrieve_scopes()),
        "redirect_uris": [f"{app_internal_url}/callback"],
        "jwks_uri": jwks_uri,
        "dsi_type": "none",
    }

    logger.info(
        f"Registering account {zoom_account_id} with OpenEMR at {registration_endpoint}"
    )

    response = requests.post(
        registration_endpoint,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15
    )

    response.raise_for_status()
    return response.json()


def _deregister_from_openemr(
    registration_client_uri: str,
    registration_access_token: str
) -> None:
    """
    Delete a client registration from OpenEMR using the management URI.

    OpenEMR returns a registration_client_uri and registration_access_token
    when you register. The management URI supports GET (read), PUT (update),
    and DELETE (remove) operations authenticated with the registration token.

    Fails silently if OpenEMR returns an error — we still want to clean up
    the local DB record and keypair even if OpenEMR deregistration fails.
    """
    try:
        response = requests.delete(
            registration_client_uri,
            headers={"Authorization": f"Bearer {registration_access_token}"},
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Deregistered client from OpenEMR: {registration_client_uri}")
    except requests.RequestException as e:
        logger.warning(
            f"OpenEMR deregistration failed (continuing cleanup anyway): {e}"
        )


def register_zoom_account(
    nickname: str | None, 
    zoom_account_id: str,
    zoom_client_id: str,
    zoom_client_secret: str,
    zoom_webhook_secret: str,
    ehr_context_username: str | None, 
    ehr_context_password: str | None,
    contact_email: str, 
    timezone: str = "America/New_York",
) -> tuple[ZoomAccount, AccountConfig]:
    """
    Full registration flow for a Zoom account.

    Step 1: Check for existing registration — don't allow duplicates.
    Step 2: Generate a per-account RSA keypair.
    Step 3: Register with OpenEMR dynamic client registration.
    Step 4: Persist ZoomAccount to DB.
    Step 5: Validate Zoom credentials and cache token.
            If this fails, roll back DB, keypair, and OpenEMR registration.
    Step 6: Trigger OpenEMR verification scheduler.

    Returns: The newly created ZoomAccount ORM object.
    Raises:
        ValueError: If account already exists or Zoom credentials are invalid.
        requests.HTTPError: If OpenEMR registration fails.
        Exception: If DB persistence fails.
    """

    # ── Step 1: Check for duplicate registration ──────────────────────────────
    existing = ZoomAccount.query.filter_by(account_id=zoom_account_id).first()
    if existing:
        if existing.is_active:
            raise ValueError(
                f"Account {zoom_account_id} is already registered and active. "
                "Deregister it first before re-registering."
            )
        else:
            logger.info(
                f"Found inactive registration for {zoom_account_id}, removing before re-register"
            )
            db.session.delete(existing)
            db.session.commit()

    # ── Step 2: Generate RSA keypair ──────────────────────────────────────────
    logger.info(f"Generating RSA keypair for account {zoom_account_id}")
    private_key_path, kid = generate_keypair(zoom_account_id)

    # ── Step 3: Register with OpenEMR ─────────────────────────────────────────
    try:
        openemr_response = _register_with_openemr(zoom_account_id, contact_email)
    except Exception as e:
        logger.error(f"OpenEMR registration failed, cleaning up keypair: {e}")
        delete_keypair(zoom_account_id)
        raise

    # ── Step 4: Persist to DB ─────────────────────────────────────────────────
    try:
        registration_client_uri = openemr_response.get("registration_client_uri", "")
        if registration_client_uri:
            openemr_public_url = current_app.config["OPENEMR_PUBLIC_URL"]
            openemr_base_url = current_app.config["OPENEMR_BASE_URL"]
            registration_client_uri = (
                openemr_response.get("registration_client_uri", "")
                .replace(openemr_public_url, openemr_base_url)
            )

        account = ZoomAccount(
            nickname=nickname,
            account_id=zoom_account_id,
            client_id=zoom_client_id,
            client_secret=zoom_client_secret,
            webhook_secret=zoom_webhook_secret,
            openemr_client_id=openemr_response["client_id"],
            openemr_client_secret=openemr_response.get("client_secret"),
            openemr_registration_access_token=openemr_response.get(
                "registration_access_token"
            ),
            openemr_registration_client_uri=registration_client_uri,
            private_key_path=private_key_path,
            kid=kid,
            tenant_id=_generate_tenant_id(zoom_account_id, zoom_client_id)
        )
        if ehr_context_username and ehr_context_password:
            account = set_ehr_context_credentials(account=account, ehr_context_username=ehr_context_username, ehr_context_password=ehr_context_password)

        db.session.add(account)

        config = AccountConfig(
            account_id=zoom_account_id,
            timezone=timezone,
        )
        db.session.add(config)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.error(f"DB persistence failed, cleaning up: {e}")
        delete_keypair(zoom_account_id)
        raise

    # ── Step 5: Validate Zoom credentials and cache token ─────────────────────
    # Account exists in DB now so _fetch_zoom_token() can write to it.
    # If this fails, roll back everything — DB record, keypair, OpenEMR registration.
    logger.info(f"Validating Zoom credentials for account {zoom_account_id}")
    if not validate_zoom_credentials(account):
        logger.error(
            f"Zoom credential validation failed for account {zoom_account_id}, "
            "rolling back registration"
        )
        # Clean up in reverse order
        _deregister_from_openemr(
            account.openemr_registration_client_uri,
            account.openemr_registration_access_token
        )
        db.session.delete(account)
        db.session.commit()
        delete_keypair(zoom_account_id)
        raise ValueError(
            f"Zoom credential validation failed for account {zoom_account_id}. "
            "Verify account_id, client_id, and client_secret are correct and "
            "the app is activated in the Zoom Marketplace."
        )

    # ── Step 6: Trigger OpenEMR verification scheduler ────────────────────────
    trigger_verification_scheduler(current_app._get_current_object())  # type: ignore[attr-defined]

    logger.info(
        f"Registration complete for account {zoom_account_id}, "
        f"OpenEMR client_id: {openemr_response['client_id']}"
    )
    return account, config


def update_zoom_account_credentials(
    zoom_account_id: str,
    nickname: str | None = None,
    zoom_client_secret: str | None = None,
    zoom_webhook_secret: str | None = None,
    ehr_context_username: str | None = None,
    ehr_context_password: str | None = None,
) -> ZoomAccount:
    """Update credential fields on ZoomAccount."""

    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()

    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    FIELD_MAP = {
        "nickname":             nickname,
        "client_secret":        zoom_client_secret,
        "webhook_secret":       zoom_webhook_secret,
    }

    updated = []
    for attr, value in FIELD_MAP.items():
        if value is not None:
            setattr(account, attr, value)
            updated.append(attr)

    # Password requires hashing — delegate to dedicated service function
    if ehr_context_username and ehr_context_password:
        account = set_ehr_context_credentials(
            account=account,
            ehr_context_username=ehr_context_username or account.ehr_context_username,
            ehr_context_password=ehr_context_password,
        )
        updated.append("ehr_context_password_hash")

    if not updated:
        raise ValueError("No valid fields provided")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Credential update failed for {zoom_account_id}: {e}")
        raise

    logger.info(f"Updated credentials for {zoom_account_id}: {updated}")
    return account

def update_account_config(
    zoom_account_id: str,
    timezone: str | None = None,
    allow_shared_zoom_user: bool | None = None,
    demo_patient_email_override_enabled: bool | None = None,
    demo_patient_email_override: str | None = None,
    demo_patient_phone_override_enabled: bool| None = None, 
    demo_patient_phone_override: str | None = None,
    note_writeback_mode: str | None = None,
) -> AccountConfig:
    """Update config fields on AccountConfig."""

    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    config = account.config
    if not config:
        config = AccountConfig(account_id=zoom_account_id)
        db.session.add(config)

    FIELD_MAP = {
        "timezone":                      timezone,
        "allow_shared_zoom_user":        allow_shared_zoom_user,
        "demo_patient_email_override_enabled": demo_patient_email_override_enabled,
        "demo_patient_email_override":   demo_patient_email_override,
        "demo_patient_phone_override_enabled": demo_patient_phone_override_enabled,
        "demo_patient_phone_override":   demo_patient_phone_override,
        "note_writeback_mode": note_writeback_mode,
    }

    updated = []
    for attr, value in FIELD_MAP.items():
        if value is not None:
            setattr(config, attr, value)
            updated.append(attr)

    if not updated:
        raise ValueError("No valid fields provided")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Config update failed for {zoom_account_id}: {e}")
        raise

    logger.info(f"Updated config for {zoom_account_id}: {updated}")
    return config


def deregister_zoom_account(zoom_account_id: str) -> None:
    """
    Full deregistration flow for a Zoom account.

    Step 1: Look up the account in the DB.
    Step 2: Deregister from OpenEMR using the management URI.
            Fails silently — we continue cleanup regardless.
    Step 3: Delete the keypair files from disk.
    Step 4: Delete the DB record.

    Raises:
        ValueError: If the account is not found.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()

    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    # ── Step 2: Deregister from OpenEMR ──────────────────────────────────────
    if account.openemr_registration_client_uri and account.openemr_registration_access_token:
        _deregister_from_openemr(
            account.openemr_registration_client_uri,
            account.openemr_registration_access_token
        )
    else:
        logger.warning(
            f"Account {zoom_account_id} missing OpenEMR registration URI or token, "
            "skipping OpenEMR deregistration"
        )

    # ── Step 3: Delete keypair ────────────────────────────────────────────────
    delete_keypair(zoom_account_id)

    # ── Step 4: Delete DB record ──────────────────────────────────────────────
    db.session.delete(account)
    db.session.commit()

    logger.info(f"Deregistration complete for account {zoom_account_id}")



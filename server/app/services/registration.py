import logging

import requests
from flask import current_app

from app.extensions import db
from app.models import ZoomAccount
from app.services.zoom import validate_zoom_credentials
from app.services.keys import generate_keypair, delete_keypair

logger = logging.getLogger(__name__)

# Scopes we request from OpenEMR for every registration.
# These are the system-level FHIR scopes needed for backend services auth.
# May need to update these and/or move them to .env/config to make it easier to udpate later
OPENEMR_SCOPES = " ".join([
    "system/Patient.read",
    "system/Appointment.read",
    "system/Practitioner.read",
    "system/Encounter.read",
    "system/Encounter.rs",
    "system/DocumentReference.read",
    "system/DocumentReference.write",
    "system/DocumentReference.rs",
    "system/DocumentReference.$docref",
])


def _register_with_openemr(
    zoom_account_id: str,
    kid: str,
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
    # openemr_public_url = current_app.config["OPENEMR_PUBLIC_URL"]
    openemr_base_url = current_app.config["OPENEMR_BASE_URL"]
    app_public_url = current_app.config["APP_PUBLIC_URL"]

    registration_endpoint = f"{openemr_base_url}/oauth2/default/registration"
    jwks_uri = f"{app_public_url}/.well-known/jwks.json"

    payload = {
        "application_type": "private",
        "client_name": f"Zoomly Bridge - {zoom_account_id}",
        "contacts": [contact_email],
        "token_endpoint_auth_method": "private_key_jwt",
        "scope": OPENEMR_SCOPES,
        "redirect_uris": [f"{app_public_url}/callback"],
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
    zoom_account_id: str,
    zoom_client_id: str,
    zoom_client_secret: str,
    zoom_webhook_secret: str,
    contact_email: str
) -> ZoomAccount:
    """
    Full registration flow for a Zoom account.

    Step 1: Validate Zoom credentials by attempting to fetch a token.
            If this fails, the credentials are wrong — abort immediately.

    Step 2: Check for existing registration — don't allow duplicates.

    Step 3: Generate a per-account RSA keypair and store it in keys/{account_id}/.
            The kid is derived from the account ID so it's traceable.

    Step 4: Register with OpenEMR dynamic client registration.
            This call goes to the public OpenEMR URL since it's an external
            HTTP request (not container-to-container).

    Step 5: Persist everything to the DB in a single transaction.
            If the DB write fails, attempt to clean up the keypair files.

    Returns: The newly created ZoomAccount ORM object.
    Raises:
        ValueError: If credentials are invalid or account already exists.
        requests.HTTPError: If OpenEMR registration fails.
        Exception: If DB persistence fails (keypair cleanup attempted).
    """

    # ── Step 1: Validate Zoom credentials ────────────────────────────────────
    logger.info(f"Validating Zoom credentials for account {zoom_account_id}")
    if not validate_zoom_credentials(zoom_account_id, zoom_client_id, zoom_client_secret):
        raise ValueError(
            f"Zoom credential validation failed for account {zoom_account_id}. "
            "Verify account_id, client_id, and client_secret are correct and "
            "the app is activated in the Zoom Marketplace."
        )

    # ── Step 2: Check for duplicate registration ──────────────────────────────
    existing = ZoomAccount.query.filter_by(account_id=zoom_account_id).first()
    if existing:
        if existing.is_active:
            raise ValueError(
                f"Account {zoom_account_id} is already registered and active. "
                "Deregister it first before re-registering."
            )
        else:
            # Inactive record exists — clean it up before re-registering
            logger.info(
                f"Found inactive registration for {zoom_account_id}, removing before re-register"
            )
            db.session.delete(existing)
            db.session.commit()

    # ── Step 3: Generate RSA keypair ──────────────────────────────────────────
    logger.info(f"Generating RSA keypair for account {zoom_account_id}")
    private_key_path, public_key_path, kid = generate_keypair(zoom_account_id)

    # ── Step 4: Register with OpenEMR ─────────────────────────────────────────
    # Note: this must happen AFTER keypair generation because the JWKS endpoint
    # needs to serve the new public key before OpenEMR fetches it at token time.
    try:
        openemr_response = _register_with_openemr(zoom_account_id, kid, contact_email)
    except Exception as e:
        # OpenEMR registration failed — clean up the keypair we just generated
        logger.error(f"OpenEMR registration failed, cleaning up keypair: {e}")
        delete_keypair(zoom_account_id)
        raise

    # ── Step 5: Persist to DB ─────────────────────────────────────────────────
    try:
        # Normalize registration_client_uri to use internal Docker URL.
        # OpenEMR returns this with the public URL, but all API calls
        # go internally so we override with the internal version from the start.
        registration_client_uri = openemr_response.get("registration_client_uri", "")
        if registration_client_uri:
            openemr_public_url = current_app.config["OPENEMR_PUBLIC_URL"]
            openemr_base_url = current_app.config["OPENEMR_BASE_URL"]
            print(openemr_base_url)
            print(openemr_public_url)
            registration_client_uri = (
                openemr_response.get("registration_client_uri", "")
                .replace(openemr_public_url, openemr_base_url)
            )
        account = ZoomAccount(
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
            is_active=True,
        )

        db.session.add(account)
        db.session.commit()

        logger.info(
            f"Registration complete for account {zoom_account_id}, "
            f"OpenEMR client_id: {openemr_response['client_id']}"
        )
        return account

    except Exception as e:
        db.session.rollback()
        # DB failed — clean up keypair to avoid orphaned files
        logger.error(f"DB persistence failed, cleaning up keypair: {e}")
        delete_keypair(zoom_account_id)
        raise


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
import logging
import requests
from sqlalchemy import text
from flask import current_app
from app.auth.jwt_assertion import get_openemr_token
from app.models import ZoomAccount, ProviderMapping
from app.extensions import db, get_openemr_db_engine

logger = logging.getLogger(__name__)


def get_practitioners(
    zoom_account: ZoomAccount,
    search: str | None = None,
    practitioner_id: str | None = None
) -> list[dict]:
    """
    Fetch Practitioner resources from OpenEMR FHIR API.

    Args:
        zoom_account: The ZoomAccount to use for authentication
        search: Optional name search string
        practitioner_id: Optional FHIR Practitioner UUID to fetch a single provider

    Returns: List of simplified provider dicts
    """
    fhir_base = current_app.config["OPENEMR_FHIR_BASE_URL"]
    token = get_openemr_token(zoom_account)

    if practitioner_id:
        url = f"{fhir_base}/Practitioner/{practitioner_id}"
    else:
        url = f"{fhir_base}/Practitioner"

    params = {}
    if search:
        params["name"] = search

    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=10
    )
    response.raise_for_status()
    data = response.json()

    if practitioner_id:
        return [_normalize_practitioner(data)]

    # Bundle response — deduplicate by id
    entries = data.get("entry", [])
    seen = set()
    practitioners = []
    for entry in entries:
        resource = entry.get("resource", {})
        fhir_id = resource.get("id")
        if fhir_id and fhir_id not in seen:
            seen.add(fhir_id)
            practitioners.append(_normalize_practitioner(resource))

    return practitioners


def get_provider_username(provider_id: int) -> str | None:
    
    engine = get_openemr_db_engine()
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT username FROM users WHERE id = :id"),
                {"id": int(provider_id)}
            ).fetchone()
            return result.username if result else None
    except Exception as e:
        logger.error(f"openemr.get_provider_username | Failed: {e}")
        return None
    

def _normalize_practitioner(resource: dict) -> dict:
    """
    Normalize a FHIR Practitioner resource into a clean dict
    for our API response.
    """
    name = resource.get("name", [{}])[0]
    given = name.get("given", [])
    family = name.get("family", "")
    prefix = name.get("prefix", [])

    npi = None
    for identifier in resource.get("identifier", []):
        if "us-npi" in identifier.get("system", ""):
            npi = identifier.get("value")
            break

    email = None
    for telecom in resource.get("telecom", []):
        if telecom.get("system") == "email":
            email = telecom.get("value")
            break

    # Look up users.id from OpenEMR DB using NPI.
    # This is the integer used as pc_aid / form_provider in appointment events
    # and needs to be stored on ProviderMapping for the webhook hot path.
    users_id = None
    if npi:
        try:
            engine = get_openemr_db_engine()
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT id FROM users WHERE npi = :npi LIMIT 1"),
                    {"npi": npi}
                ).fetchone()
                if row:
                    users_id = row.id
        except Exception as e:
            logger.warning(f"_normalize_practitioner | Failed to look up users.id for npi={npi}: {e}")

    return {
        "fhir_id": resource.get("id"),
        "active": resource.get("active", False),
        "first_name": " ".join(given),
        "last_name": family,
        "full_name": f"{' '.join(prefix)} {' '.join(given)} {family}".strip(),
        "npi": npi,
        "email": email,
        "users_id": users_id,
    }


def _create_provider_mapping(
    zoom_account_id: str,
    openemr_fhir_id: str,
    openemr_provider_npi: str,
    openemr_provider_id: int | None,
    openemr_provider_name: str | None,
    zoom_user_id: str,
    zoom_user_email: str,
    zoom_user_name: str | None,
    zoom_user_type: int | None
) -> ProviderMapping:
    """
    Create a new provider mapping linking an OpenEMR provider to a Zoom user.

    Raises:
        ValueError: If account not found, mapping already exists, or the provider
        doesn't have a paid Zoom license - basic is not accepted
    """
    # Validate Zoom license type
    if zoom_user_type == 1:
        raise ValueError(
            f"Zoom user {zoom_user_email} has a Basic (free) license. "
            "A paid Zoom license is required for telehealth features. "
            "Please assign a Licensed seat to this user in the Zoom admin portal."
        )
    
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    # Check for duplicate — same NPI already mapped for this account
    existing = ProviderMapping.query.filter_by(
        zoom_account_id=zoom_account_id,
        openemr_provider_npi=openemr_provider_npi,
        is_active=True
    ).first()
    if existing:
        raise ValueError(
            f"Provider NPI {openemr_provider_npi} is already mapped to "
            f"{existing.zoom_user_email} for this account"
        )

    mapping = ProviderMapping(
        zoom_account_id=zoom_account_id,
        openemr_fhir_id=openemr_fhir_id,
        openemr_provider_npi=openemr_provider_npi,
        openemr_provider_id=openemr_provider_id, 
        openemr_provider_name=openemr_provider_name,
        zoom_user_id=zoom_user_id,
        zoom_user_email=zoom_user_email,
        zoom_user_name=zoom_user_name,
        zoom_user_type=zoom_user_type,
        is_active=True
    )

    db.session.add(mapping)
    db.session.commit()

    logger.info(
        f"Provider mapping created: NPI {openemr_provider_npi} "
        f"→ Zoom user {zoom_user_email}"
    )
    return mapping


def _get_provider_mappings(zoom_account_id: str) -> list[ProviderMapping]:
    """
    Get all active provider mappings for a Zoom account.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    return ProviderMapping.query.filter_by(
        zoom_account_id=zoom_account_id,
        is_active=True
    ).all()


def _delete_provider_mapping(zoom_account_id: str, openemr_provider_id: str) -> None:
    """
    Delete a provider mapping by npi.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    mapping = ProviderMapping.query.filter_by(
        openemr_provider_id=openemr_provider_id,
        zoom_account_id=zoom_account_id,
        is_active=True
    ).first()
    if not mapping:
        raise ValueError(f"No active mapping found with NPI {openemr_provider_id}")

    db.session.delete(mapping)
    db.session.commit()
    logger.info(f"Provider mapping for NPI {openemr_provider_id} deleted")
import logging
from app.extensions import db
from app.models import ZoomAccount, ProviderMapping

logger = logging.getLogger(__name__)


def create_provider_mapping(
    zoom_account_id: str,
    openemr_fhir_id: str,
    openemr_provider_npi: str,
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
        zoom_account_id=account.id,
        openemr_provider_npi=openemr_provider_npi,
        is_active=True
    ).first()
    if existing:
        raise ValueError(
            f"Provider NPI {openemr_provider_npi} is already mapped to "
            f"{existing.zoom_user_email} for this account"
        )

    mapping = ProviderMapping(
        zoom_account_id=account.id,
        openemr_fhir_id=openemr_fhir_id,
        openemr_provider_npi=openemr_provider_npi,
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


def get_provider_mappings(zoom_account_id: str) -> list[ProviderMapping]:
    """
    Get all active provider mappings for a Zoom account.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    return ProviderMapping.query.filter_by(
        zoom_account_id=account.id,
        is_active=True
    ).all()


def delete_provider_mapping(zoom_account_id: str, mapping_id: int) -> None:
    """
    Delete a provider mapping by ID.
    """
    account = ZoomAccount.query.filter_by(
        account_id=zoom_account_id, is_active=True
    ).first()
    if not account:
        raise ValueError(f"No active registration found for account {zoom_account_id}")

    mapping = ProviderMapping.query.filter_by(
        id=mapping_id,
        zoom_account_id=account.id,
        is_active=True
    ).first()
    if not mapping:
        raise ValueError(f"No active mapping found with id {mapping_id}")

    db.session.delete(mapping)
    db.session.commit()
    logger.info(f"Provider mapping {mapping_id} deleted")
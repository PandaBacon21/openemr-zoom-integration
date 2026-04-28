import pytest

from app.extensions import db
from app.models import ProviderMapping, ZoomAccount
from app.services.openemr import provider as providers


def _create_account(account_id: str, *, is_active: bool = True) -> ZoomAccount:
    account = ZoomAccount(
        account_id=account_id,
        client_id="zoom-client-id",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id="openemr-client-id",
        private_key_path="/tmp/private.pem",
        kid=f"zoomly-{account_id}",
        is_active=is_active,
    )
    db.session.add(account)
    db.session.commit()
    return account


def _create_mapping(account: ZoomAccount, *, npi: str, is_active: bool = True) -> ProviderMapping:
    mapping = ProviderMapping(
        zoom_account_id=account.account_id,
        openemr_fhir_id=f"fhir-{npi}",
        openemr_provider_npi=npi,
        openemr_provider_id=f"id-{npi}",
        openemr_provider_name=f"Provider {npi}",
        zoom_user_id=f"user-{npi}",
        zoom_user_email=f"user-{npi}@example.com",
        zoom_user_name=f"User {npi}",
        zoom_user_type=2,
        is_active=is_active,
    )
    db.session.add(mapping)
    db.session.commit()
    return mapping


def test_create_provider_mapping_rejects_basic_zoom_license(app):
    with app.app_context():
        with pytest.raises(ValueError, match="Basic \\(free\\) license"):
            providers._create_provider_mapping(
                zoom_account_id="acct-1",
                openemr_fhir_id="pract-1",
                openemr_provider_npi="1234567890",
                openemr_provider_id=10,
                openemr_provider_name="Dr Jane Doe",
                zoom_user_id="u-1",
                zoom_user_email="jane@example.com",
                zoom_user_name="Dr Jane Doe",
                zoom_user_type=1,
            )


def test_create_provider_mapping_requires_active_registration(app):
    with app.app_context():
        with pytest.raises(ValueError, match="No active registration found for account missing"):
            providers._create_provider_mapping(
                zoom_account_id="missing",
                openemr_fhir_id="pract-1",
                openemr_provider_npi="1234567890",
                openemr_provider_id=10,
                openemr_provider_name="Dr Jane Doe",
                zoom_user_id="u-1",
                zoom_user_email="jane@example.com",
                zoom_user_name="Dr Jane Doe",
                zoom_user_type=2,
            )


def test_create_provider_mapping_rejects_duplicate_npi_for_account(app):
    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        _create_mapping(account, npi="1234567890", is_active=True)

        with pytest.raises(ValueError, match="already mapped"):
            providers._create_provider_mapping(
                zoom_account_id="acct-1",
                openemr_fhir_id="pract-2",
                openemr_provider_npi="1234567890",
                openemr_provider_id=10,
                openemr_provider_name="Dr New",
                zoom_user_id="u-2",
                zoom_user_email="new@example.com",
                zoom_user_name="Dr New",
                zoom_user_type=2,
            )


def test_create_provider_mapping_allows_replacing_inactive_mapping(app):
    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        _create_mapping(account, npi="1234567890", is_active=False)

        mapping = providers._create_provider_mapping(
            zoom_account_id="acct-1",
            openemr_fhir_id="pract-2",
            openemr_provider_npi="1234567890",
            openemr_provider_id=10,
            openemr_provider_name="Dr New",
            zoom_user_id="u-2",
            zoom_user_email="new@example.com",
            zoom_user_name="Dr New",
            zoom_user_type=2,
        )

        rows = ProviderMapping.query.filter_by(zoom_account_id=account.account_id).all()

    assert mapping.openemr_provider_npi == "1234567890"
    assert mapping.openemr_provider_id == "10"
    assert mapping.zoom_user_email == "new@example.com"
    assert len(rows) == 2


def test_get_provider_mappings_returns_only_active_for_account(app):
    with app.app_context():
        account_1 = _create_account("acct-1", is_active=True)
        account_2 = _create_account("acct-2", is_active=True)

        active = _create_mapping(account_1, npi="1234567890", is_active=True)
        _create_mapping(account_1, npi="2234567890", is_active=False)
        _create_mapping(account_2, npi="3234567890", is_active=True)

        result = providers._get_provider_mappings("acct-1")

    assert [m.id for m in result] == [active.id]


def test_get_provider_mappings_requires_active_registration(app):
    with app.app_context():
        with pytest.raises(ValueError, match="No active registration found for account missing"):
            providers._get_provider_mappings("missing")


def test_delete_provider_mapping_deletes_matching_mapping(app):
    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        mapping = _create_mapping(account, npi="1234567890", is_active=True)

        providers._delete_provider_mapping("acct-1", mapping.openemr_provider_id)
        deleted = ProviderMapping.query.filter_by(id=mapping.id).first()

    assert deleted is None


def test_delete_provider_mapping_raises_when_not_found(app):
    with app.app_context():
        _create_account("acct-1", is_active=True)
        with pytest.raises(ValueError, match="No active mapping found with NPI 999"):
            providers._delete_provider_mapping("acct-1", "999")

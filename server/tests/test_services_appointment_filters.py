import pytest

from app.extensions import db
from app.models import AppointmentTypeFilter, ZoomAccount
from app.services.openemr.appointments import appointment_filters


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


def _create_filter(account: ZoomAccount, type_id: str, type_name: str) -> AppointmentTypeFilter:
    entry = AppointmentTypeFilter(
        zoom_account_id=account.account_id,
        openemr_type_id=type_id,
        openemr_type_name=type_name,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def test_create_appointment_filter_requires_active_registration(app):
    with app.app_context():
        with pytest.raises(ValueError, match="No active registration found for account missing"):
            appointment_filters._create_appointment_filter(
                zoom_account_id="missing",
                openemr_type_id="1",
                openemr_type_name="Telehealth",
                logger=__import__("logging").getLogger("test"),
            )


def test_create_appointment_filter_rejects_duplicate_type(app):
    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        _create_filter(account, "1", "Telehealth")

        with pytest.raises(ValueError, match="already in the filter list"):
            appointment_filters._create_appointment_filter(
                zoom_account_id="acct-1",
                openemr_type_id="1",
                openemr_type_name="Telehealth",
                logger=__import__("logging").getLogger("test"),
            )


def test_create_appointment_filter_success(app):
    with app.app_context():
        _create_account("acct-1", is_active=True)
        entry = appointment_filters._create_appointment_filter(
            zoom_account_id="acct-1",
            openemr_type_id="2",
            openemr_type_name="Follow-up",
            logger=__import__("logging").getLogger("test"),
        )
        stored = AppointmentTypeFilter.query.filter_by(id=entry.id).first()

    assert entry.openemr_type_id == "2"
    assert entry.openemr_type_name == "Follow-up"
    assert stored is not None


def test_get_appointment_filters_requires_active_registration(app):
    with app.app_context():
        with pytest.raises(ValueError, match="No active registration found for account missing"):
            appointment_filters._get_appointment_filters("missing")


def test_get_appointment_filters_returns_only_for_requested_account(app):
    with app.app_context():
        account_1 = _create_account("acct-1", is_active=True)
        account_2 = _create_account("acct-2", is_active=True)

        keep_1 = _create_filter(account_1, "10", "Telehealth Consult")
        keep_2 = _create_filter(account_1, "20", "Follow-up")
        _create_filter(account_2, "30", "Different Account")

        filters = appointment_filters._get_appointment_filters("acct-1")

    assert sorted(f.id for f in filters) == sorted([keep_1.id, keep_2.id])


def test_delete_appointment_filter_requires_active_registration(app):
    with app.app_context():
        with pytest.raises(ValueError, match="No active registration found for account missing"):
            appointment_filters._delete_appointment_filter("missing", "10", __import__("logging").getLogger("test"))


def test_delete_appointment_filter_raises_when_not_found(app):
    with app.app_context():
        _create_account("acct-1", is_active=True)
        with pytest.raises(ValueError, match="No filter found with id 999"):
            appointment_filters._delete_appointment_filter("acct-1", "999", __import__("logging").getLogger("test"))


def test_delete_appointment_filter_deletes_entry(app):
    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        entry = _create_filter(account, "10", "Telehealth Consult")

        appointment_filters._delete_appointment_filter("acct-1", "10", __import__("logging").getLogger("test"))
        deleted = AppointmentTypeFilter.query.filter_by(id=entry.id).first()

    assert deleted is None


# --- integration split -----------------------------------------------------

_LOG = __import__("logging").getLogger("test")


def test_create_appointment_filter_defaults_to_epic(app):
    with app.app_context():
        _create_account("acct-1", is_active=True)
        entry = appointment_filters._create_appointment_filter(
            zoom_account_id="acct-1",
            openemr_type_id="27",
            openemr_type_name="Epic Type",
            logger=_LOG,
        )
        assert entry.integration == "epic"


def test_create_appointment_filter_stores_veradigm_integration(app):
    with app.app_context():
        _create_account("acct-1", is_active=True)
        entry = appointment_filters._create_appointment_filter(
            zoom_account_id="acct-1",
            openemr_type_id="90",
            openemr_type_name="Veradigm Type",
            logger=_LOG,
            integration="veradigm",
        )
        assert entry.integration == "veradigm"


def test_create_appointment_filter_rejects_invalid_integration(app):
    with app.app_context():
        _create_account("acct-1", is_active=True)
        with pytest.raises(ValueError, match="Invalid integration"):
            appointment_filters._create_appointment_filter(
                zoom_account_id="acct-1",
                openemr_type_id="1",
                openemr_type_name="Bad",
                logger=_LOG,
                integration="cerner",
            )


def test_get_appointment_filters_filters_by_integration(app):
    with app.app_context():
        _create_account("acct-1", is_active=True)
        appointment_filters._create_appointment_filter(
            zoom_account_id="acct-1", openemr_type_id="27",
            openemr_type_name="Epic", logger=_LOG, integration="epic",
        )
        appointment_filters._create_appointment_filter(
            zoom_account_id="acct-1", openemr_type_id="90",
            openemr_type_name="Veradigm", logger=_LOG, integration="veradigm",
        )

        veradigm = appointment_filters._get_appointment_filters("acct-1", integration="veradigm")
        all_rows = appointment_filters._get_appointment_filters("acct-1")

    assert [f.openemr_type_id for f in veradigm] == ["90"]
    assert len(all_rows) == 2

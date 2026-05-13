from app.extensions import db
from app.models import AccountConfig, AppointmentTypeFilter, ProviderMapping, ZoomAccount
from app.services.openemr.appointments import appointment_processor


BASE_PAYLOAD = {
    "event": "appointment.set",
    "eid": 999,
    "pid": 1,
    "provider_id": 10,
    "category_id": 27,
    "appointment_date": "20260420",
    "appointment_time": "10:00",
    "appt_status": "^",
    "facility_id": 1,
    "comments": "Test appointment",
    "fired_at": "2026-04-19T14:00:00+00:00",
}


def _create_account(account_id: str, *, is_active: bool = True) -> ZoomAccount:
    account = ZoomAccount(
        account_id=account_id,
        client_id="zoom-client-id",
        client_secret="zoom-client-secret",
        webhook_secret="zoom-webhook-secret",
        openemr_client_id="openemr-client-id",
        private_key_path=f"/tmp/keys/{account_id}/private.pem",
        kid=f"zoomly-{account_id}",
        is_active=is_active,
    )
    db.session.add(account)
    db.session.add(AccountConfig(account_id=account_id, timezone="America/Denver"))
    db.session.commit()
    return account


def _create_provider_mapping(
    account: ZoomAccount,
    *,
    npi: str = "1234567890",
    provider_id: str = "10",
) -> ProviderMapping:
    mapping = ProviderMapping(
        zoom_account_id=account.account_id,
        openemr_fhir_id="pract-1",
        openemr_provider_npi=npi,
        openemr_provider_id=provider_id,
        openemr_provider_name="Dr Jane Doe",
        zoom_user_id="u-1",
        zoom_user_email="jane@example.com",
        zoom_user_name="Dr Jane Doe",
        zoom_user_type=2,
        is_active=True,
    )
    db.session.add(mapping)
    db.session.commit()
    return mapping


def _create_type_filter(account: ZoomAccount, type_id: str) -> AppointmentTypeFilter:
    f = AppointmentTypeFilter(
        zoom_account_id=account.account_id,
        openemr_type_id=type_id,
        openemr_type_name=f"Type {type_id}",
    )
    db.session.add(f)
    db.session.commit()
    return f


def test_filter_appointment_event_drops_when_provider_missing():
    payload = dict(BASE_PAYLOAD)
    payload.pop("provider_id")
    matches, reason = appointment_processor.filter_appointment_event(payload)
    assert matches == []
    assert reason == "missing_provider_id"


def test_filter_appointment_event_drops_by_provider_id(app):
    payload = dict(BASE_PAYLOAD)
    payload["provider_id"] = 99

    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        _create_provider_mapping(account, npi="1234567890", provider_id="10")
        matches, reason = appointment_processor.filter_appointment_event(payload)
    assert matches == []
    assert reason == "provider_unmapped"


def test_filter_appointment_event_matches_when_no_type_filters(app):
    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        mapping = _create_provider_mapping(account, npi="1234567890", provider_id="10")

        payload = dict(BASE_PAYLOAD)
        payload["category_id"] = 99  # no filters configured => all types pass
        matches, reason = appointment_processor.filter_appointment_event(payload)

    assert len(matches) == 1
    assert matches[0].zoom_account.account_id == "acct-1"
    assert matches[0].provider_mapping.id == mapping.id
    assert matches[0].payload["eid"] == 999
    assert reason is None


def test_filter_appointment_event_drops_by_category_id(app):
    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        _create_provider_mapping(account, npi="1234567890", provider_id="10")
        _create_type_filter(account, "27")

        payload = dict(BASE_PAYLOAD)
        payload["category_id"] = 99
        matches, reason = appointment_processor.filter_appointment_event(payload)
    assert matches == []
    assert reason == "type_mismatch"


def test_filter_appointment_event_matches_allowed_category(app):
    with app.app_context():
        account = _create_account("acct-1", is_active=True)
        _create_provider_mapping(account, npi="1234567890", provider_id="10")
        _create_type_filter(account, "27")

        payload = dict(BASE_PAYLOAD)
        payload["category_id"] = 27
        matches, reason = appointment_processor.filter_appointment_event(payload)

    assert len(matches) == 1
    assert matches[0].zoom_account.account_id == "acct-1"
    assert reason is None


def test_filter_appointment_event_skips_mapping_when_account_inactive(app):
    with app.app_context():
        account = _create_account("acct-1", is_active=False)
        _create_provider_mapping(account, npi="1234567890", provider_id="10")

        payload = dict(BASE_PAYLOAD)
        matches, reason = appointment_processor.filter_appointment_event(payload)

    assert matches == []
    assert reason == "account_inactive"

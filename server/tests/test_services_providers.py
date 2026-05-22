from datetime import date, time, timedelta
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models import ProviderMapping, ZoomAccount
from app.services.openemr import provider as providers


def _fake_patient_engine(rows):
    """Mimics a SQLAlchemy engine where .connect().execute(...).fetchall() returns rows."""
    class FakeResult:
        def fetchall(self):
            return rows

    class FakeConn:
        def execute(self, query, params):
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    return FakeEngine()


def _fake_row_engine(row):
    """Single-row variant: .connect().execute(...).fetchone() returns the row (or None)."""
    class FakeResult:
        def fetchone(self):
            return row

    class FakeConn:
        def execute(self, query, params):
            return FakeResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return FakeConn()

    return FakeEngine()


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


def test_get_provider_patients_returns_seeded_three(monkeypatch):
    rows = [
        SimpleNamespace(pid=108, fname="Thomas",  lname="Walsh",    DOB=date(1969, 8, 19),  sex="Male"),
        SimpleNamespace(pid=100, fname="James",   lname="Harrison", DOB=date(1978, 3, 14),  sex="Male"),
        SimpleNamespace(pid=112, fname="Omar",    lname="Hassan",   DOB=date(1975, 3, 29),  sex="Male"),
    ]
    # Engine sorts by pid in real SQL; mock returns whatever the engine gives us. The
    # function returns rows verbatim, so we hand them back already in pid-asc order to
    # mirror what MariaDB would do.
    sorted_rows = sorted(rows, key=lambda r: r.pid)
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_patient_engine(sorted_rows),
    )

    result = providers.get_provider_patients(10)

    assert [p["pid"] for p in result] == [100, 108, 112]
    assert result[0] == {
        "pid": 100,
        "fname": "James",
        "lname": "Harrison",
        "dob": "1978-03-14",
        "sex": "Male",
    }


def test_get_provider_patients_empty_for_unknown_provider(monkeypatch):
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_patient_engine([]),
    )

    assert providers.get_provider_patients(9999) == []


def test_get_provider_patients_handles_null_dob(monkeypatch):
    rows = [
        SimpleNamespace(pid=200, fname="Anon", lname="Patient", DOB=None, sex="Female"),
    ]
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_patient_engine(rows),
    )

    assert providers.get_provider_patients(42)[0]["dob"] is None


# -- get_provider_specialty_categories --------------------------------------

def test_get_provider_specialty_categories_pc(monkeypatch):
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_row_engine(SimpleNamespace(specialty="Internal Medicine")),
    )
    assert providers.get_provider_specialty_categories(10) == [
        "Zoom Chronic Care",
        "Zoom New Patient",
        "Zoom Preventive",
    ]


def test_get_provider_specialty_categories_bh_psychiatry(monkeypatch):
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_row_engine(SimpleNamespace(specialty="Psychiatry")),
    )
    assert providers.get_provider_specialty_categories(12) == ["Zoom Behavioral Health"]


def test_get_provider_specialty_categories_mat(monkeypatch):
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_row_engine(SimpleNamespace(specialty="Addiction Medicine")),
    )
    assert providers.get_provider_specialty_categories(22) == ["Zoom MAT (Suboxone)"]


def test_get_provider_specialty_categories_unknown_specialty(monkeypatch):
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_row_engine(SimpleNamespace(specialty="Cardiology")),
    )
    assert providers.get_provider_specialty_categories(99) == []


def test_get_provider_specialty_categories_no_user_row(monkeypatch):
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_row_engine(None),
    )
    assert providers.get_provider_specialty_categories(9999) == []


def test_get_provider_specialty_categories_returns_fresh_list(monkeypatch):
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_row_engine(SimpleNamespace(specialty="Internal Medicine")),
    )
    first = providers.get_provider_specialty_categories(10)
    first.pop()
    second = providers.get_provider_specialty_categories(10)
    assert len(second) == 3  # not mutated by the prior pop


# -- get_provider_appointments_in_window ------------------------------------

def test_get_provider_appointments_in_window_returns_rows(monkeypatch):
    rows = [
        SimpleNamespace(
            pc_eid=501,
            pc_pid="100",
            pc_aid=10,
            pc_eventDate=date(2026, 5, 22),
            pc_startTime=timedelta(hours=9),
            pc_duration=1800,
            pc_catid=20,
            pc_apptstatus="-",
            pc_website="https://zoom.us/j/123",
            pc_title="Zoom BH",
            pc_hometext="follow up",
        ),
        SimpleNamespace(
            pc_eid=502,
            pc_pid="108",
            pc_aid=10,
            pc_eventDate=date(2026, 5, 22),
            pc_startTime=timedelta(hours=14),
            pc_duration=1800,
            pc_catid=21,
            pc_apptstatus="-",
            pc_website=None,
            pc_title="Zoom Chronic Care",
            pc_hometext="",
        ),
    ]
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_patient_engine(rows),
    )

    result = providers.get_provider_appointments_in_window(
        10, date(2026, 5, 22), date(2026, 5, 23)
    )

    assert len(result) == 2
    assert result[0]["pc_eid"] == 501
    assert result[0]["pc_startTime"] == time(9, 0, 0)
    assert result[1]["pc_startTime"] == time(14, 0, 0)
    assert result[1]["pc_website"] is None


def test_get_provider_appointments_in_window_empty(monkeypatch):
    monkeypatch.setattr(
        "app.services.openemr.provider.get_openemr_db_engine",
        lambda: _fake_patient_engine([]),
    )
    assert providers.get_provider_appointments_in_window(
        10, date(2026, 5, 22), date(2026, 5, 23)
    ) == []


def test_timedelta_to_time_handles_none():
    assert providers._timedelta_to_time(None) is None
    assert providers._timedelta_to_time(timedelta(hours=8, minutes=30)) == time(8, 30, 0)
    assert providers._timedelta_to_time(timedelta(seconds=45)) == time(0, 0, 45)

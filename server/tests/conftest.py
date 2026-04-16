import os
from pathlib import Path

import pytest

# Force test-safe env before any `app.*` module import during test collection.
# Use direct assignment (not setdefault) so local/dev env vars cannot point tests
# at a real app database by accident.
os.environ["DATABASE_URL"] = "sqlite:////tmp/zoomly-tests.db"
os.environ["LOG_FILE"] = "/tmp/zoomly-tests.log"
os.environ["ENCRYPTION_KEY"] = "0123456789abcdef0123456789abcdef"
os.environ["KEYS_BASE_DIR"] = "/tmp/zoomly-test-keys"
os.environ["ZOOM_TOKEN_URL"] = "https://zoom.us/oauth/token"
os.environ["ZOOM_API_BASE_URL"] = "https://api.zoom.us/v2"
os.environ["API_KEY"] = "test-api-key"


@pytest.fixture()
def app(tmp_path: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"
    os.environ["LOG_FILE"] = str(tmp_path / "logs" / "test.log")

    from app import create_app

    flask_app = create_app("development")
    flask_app.config.update(
        TESTING=True,
        KEYS_BASE_DIR=str(tmp_path / "keys"),
        OPENEMR_CLIENT_ID="test-client-id",
        OPENEMR_BASE_URL="http://openemr.internal",
        OPENEMR_PUBLIC_URL="https://openemr.public",
        OPENEMR_FHIR_BASE_URL="http://openemr.internal/apis/default/fhir",
        APP_PUBLIC_URL="http://localhost:5000",
        JWKS_PRIVATE_PATH=str(tmp_path / "keys" / "private.pem"),
        KEY_ID="test-key-id",
        OPENEMR_SCOPES=[
            "system/Patient.read",
            "system/Appointment.read",
            "system/Encounter.read",
        ],
    )
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_openemr_token_cache():
    from app.auth import jwt_assertion

    token_cache = getattr(jwt_assertion, "_token_cache", None)
    if isinstance(token_cache, dict):
        token_cache["access_token"] = None
        token_cache["expires_at"] = 0


@pytest.fixture(autouse=True)
def reset_database(app):
    from app.extensions import db

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield

    with app.app_context():
        db.session.remove()
        db.drop_all()

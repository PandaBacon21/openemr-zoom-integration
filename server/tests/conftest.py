import os
from pathlib import Path

import pytest


@pytest.fixture()
def app(tmp_path: Path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"
    os.environ["LOG_FILE"] = str(tmp_path / "logs" / "test.log")

    from app import create_app

    flask_app = create_app("development")
    flask_app.config.update(
        TESTING=True,
        OPENEMR_CLIENT_ID="test-client-id",
        OPENEMR_BASE_URL="http://openemr.internal",
        OPENEMR_PUBLIC_URL="https://openemr.public",
        JWKS_PRIVATE_PATH=str(tmp_path / "keys" / "private.pem"),
        KEY_ID="test-key-id",
    )
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_openemr_token_cache():
    from app.auth import jwt_assertion

    jwt_assertion._token_cache["access_token"] = None
    jwt_assertion._token_cache["expires_at"] = 0

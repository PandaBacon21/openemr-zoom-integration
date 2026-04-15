import os
import stat
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from app.services import keys


def test_key_path_helpers_use_account_directory(app):
    with app.app_context():
        account_id = "acct-123"
        key_dir = keys.get_key_dir(account_id)
        private_path = keys.get_private_key_path(account_id)
        public_path = keys.get_public_key_path(account_id)

    assert key_dir.endswith("/acct-123")
    assert private_path.endswith("/acct-123/private.pem")
    assert public_path.endswith("/acct-123/public.pem")


def test_generate_keypair_creates_expected_files(app):
    with app.app_context():
        private_key_path, kid = keys.generate_keypair("acct-1")
        public_key_path = keys.get_public_key_path("acct-1")

    assert os.path.exists(private_key_path)
    assert os.path.exists(public_key_path)
    assert kid == "zoomly-acct-1"

    private_mode = stat.S_IMODE(os.stat(private_key_path).st_mode)
    public_mode = stat.S_IMODE(os.stat(public_key_path).st_mode)
    assert private_mode == 0o600
    assert public_mode == 0o644


def test_load_private_key_reads_key(app):
    with app.app_context():
        keys.generate_keypair("acct-2")
        private_key = keys.load_private_key("acct-2")

    assert isinstance(private_key, RSAPrivateKey)


def test_delete_keypair_removes_files_and_directory(app):
    with app.app_context():
        private_key_path, _ = keys.generate_keypair("acct-3")
        public_key_path = keys.get_public_key_path("acct-3")
        key_dir = keys.get_key_dir("acct-3")
        keys.delete_keypair("acct-3")

    assert not os.path.exists(private_key_path)
    assert not os.path.exists(public_key_path)
    assert not os.path.exists(key_dir)


def test_delete_keypair_is_idempotent(app):
    with app.app_context():
        keys.delete_keypair("does-not-exist")


def test_build_jwks_for_accounts_skips_missing_metadata(app):
    account_missing_kid = SimpleNamespace(
        account_id="acct-a",
        kid=None,
        private_key_path="/tmp/unused.pem",
    )
    account_missing_key_path = SimpleNamespace(
        account_id="acct-b",
        kid="zoomly-acct-b",
        private_key_path=None,
    )

    with app.app_context():
        jwks = keys.build_jwks_for_accounts([account_missing_kid, account_missing_key_path])

    assert jwks == {"keys": []}


def test_build_jwks_for_accounts_skips_missing_files(app):
    account = SimpleNamespace(
        account_id="acct-missing",
        kid="zoomly-acct-missing",
        private_key_path="/tmp/not-found/private.pem",
    )

    with app.app_context():
        jwks = keys.build_jwks_for_accounts([account])

    assert jwks == {"keys": []}


def test_build_jwks_for_accounts_returns_keys_for_active_accounts(app):
    with app.app_context():
        key1_private, _ = keys.generate_keypair("acct-10")
        key2_private, _ = keys.generate_keypair("acct-20")

        accounts = [
            SimpleNamespace(account_id="acct-10", kid="zoomly-acct-10", private_key_path=key1_private),
            SimpleNamespace(account_id="acct-20", kid="zoomly-acct-20", private_key_path=key2_private),
        ]
        jwks = keys.build_jwks_for_accounts(accounts)

    assert len(jwks["keys"]) == 2
    assert sorted(k["kid"] for k in jwks["keys"]) == ["zoomly-acct-10", "zoomly-acct-20"]

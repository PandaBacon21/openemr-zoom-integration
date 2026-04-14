from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from app.auth.jwks import build_jwks, generate_rsa_key_pair, load_private_key


def test_generate_and_load_private_key(tmp_path):
    key_path = tmp_path / "keys" / "private.pem"

    generate_rsa_key_pair(str(key_path))
    private_key = load_private_key(str(key_path))

    assert key_path.exists()
    assert isinstance(private_key, RSAPrivateKey)


def test_load_private_key_generates_missing_file(tmp_path):
    key_path = tmp_path / "keys" / "private.pem"

    private_key = load_private_key(str(key_path))

    assert key_path.exists()
    assert isinstance(private_key, RSAPrivateKey)


def test_build_jwks_contains_expected_shape(tmp_path):
    key_path = tmp_path / "keys" / "private.pem"
    key_id = "demo-key-id"

    jwks = build_jwks(str(key_path), key_id)

    assert "keys" in jwks
    assert len(jwks["keys"]) == 1
    key = jwks["keys"][0]
    assert key["kty"] == "RSA"
    assert key["kid"] == key_id
    assert key["use"] == "sig"
    assert "n" in key
    assert "e" in key

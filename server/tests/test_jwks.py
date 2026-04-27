from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from app.auth.jwks import generate_rsa_key_pair, load_private_key


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

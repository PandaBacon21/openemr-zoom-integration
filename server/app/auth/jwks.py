import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from authlib.jose import JsonWebKey


def generate_rsa_key_pair(key_path: str) -> None:
    """Generate a new RSA key pair and save the private key to disk."""
    os.makedirs(os.path.dirname(key_path), exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    with open(key_path, "wb") as f:
        f.write(pem)


def load_private_key(key_path: str):
    """Load the RSA private key from disk. Generate it first if it doesn't exist."""
    if not os.path.exists(key_path):
        generate_rsa_key_pair(key_path)

    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )


def build_jwks(key_path: str, key_id: str) -> dict:
    """
    Build the JWKS response using authlib.
    OpenEMR fetches this from /.well-known/jwks.json to verify our JWT signatures.
    """
    private_key = load_private_key(key_path)

    # Export the public key as PEM so authlib can import it
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # authlib handles all the base64url encoding and JWKS formatting
    jwk = JsonWebKey.import_key(public_pem, {"kty": "RSA", "use": "sig", "kid": key_id}) # type: ignore
    return {"keys": [dict(jwk)]}
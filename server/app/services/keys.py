import logging
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from authlib.jose import JsonWebKey
from flask import current_app

logger = logging.getLogger(__name__)


def _get_keys_base_dir() -> str:
    """
    Returns the base directory where all keypairs are stored.
    Each account gets its own subdirectory: keys/{zoom_account_id}/
    Falls back to ./keys if KEYS_BASE_DIR is not configured.
    """
    return current_app.config.get("KEYS_BASE_DIR", "./keys")


def get_key_dir(zoom_account_id: str) -> str:
    """Returns the directory path for a specific account's keypair."""
    return os.path.join(_get_keys_base_dir(), zoom_account_id)


def get_private_key_path(zoom_account_id: str) -> str:
    return os.path.join(get_key_dir(zoom_account_id), "private.pem")


def get_public_key_path(zoom_account_id: str) -> str:
    return os.path.join(get_key_dir(zoom_account_id), "public.pem")


def generate_keypair(zoom_account_id: str) -> tuple[str, str, str]:
    """
    Generate a new RSA-2048 keypair for a Zoom account and save to disk.

    RSA-2048 - Required by OpenEMR's SMART Backend Services implementation

    The private key is saved with 600 permissions (owner read/write only).
    The public key is saved with 644 permissions (world readable — it has to be,
    since OpenEMR fetches it from JWKS endpoint).

    Returns: (private_key_path, public_key_path, kid)
    The kid (key ID) is derived from the zoom_account_id so it's deterministic
    and meaningful — easy to trace which account a JWT belongs to.
    """
    key_dir = get_key_dir(zoom_account_id)
    os.makedirs(key_dir, exist_ok=True)

    # Generate the RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Serialize private key to PEM format — no password encryption on the file
    # itself since the file permissions and key directory access control protect it
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Serialize public key to PEM format
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    private_key_path = get_private_key_path(zoom_account_id)
    public_key_path = get_public_key_path(zoom_account_id)

    # Write private key — restricted permissions
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    os.chmod(private_key_path, 0o600)

    # Write public key — world readable
    with open(public_key_path, "wb") as f:
        f.write(public_pem)
    os.chmod(public_key_path, 0o644)

    # kid is derived from the account ID — deterministic and traceable
    kid = f"zoomly-{zoom_account_id}"

    logger.info(f"Generated RSA keypair for account {zoom_account_id}, kid={kid}")

    return private_key_path, public_key_path, kid


def delete_keypair(zoom_account_id: str) -> None:
    """
    Delete the keypair files for a Zoom account.
    Called when an account is deregistered.
    Fails silently if files don't exist — idempotent by design.
    """
    for path in [get_private_key_path(zoom_account_id), get_public_key_path(zoom_account_id)]:
        try:
            os.remove(path)
            logger.info(f"Deleted key file: {path}")
        except FileNotFoundError:
            pass

    # Remove the directory if empty
    key_dir = get_key_dir(zoom_account_id)
    try:
        os.rmdir(key_dir)
        logger.info(f"Removed key directory: {key_dir}")
    except (FileNotFoundError, OSError):
        pass


def load_private_key(zoom_account_id: str):
    """
    Load the RSA private key for a given account from disk.
    Returns a cryptography RSAPrivateKey object.
    Raises FileNotFoundError if the key doesn't exist.
    """
    path = get_private_key_path(zoom_account_id)

    with open(path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )


def build_jwks_for_accounts(accounts: list) -> dict:
    """
    Build a JWKS response containing public keys for all active accounts.

    This is what the /.well-known/jwks.json endpoint serves.
    Each account has its own keypair with a unique kid.
    OpenEMR fetches this endpoint and finds the right key by matching
    the kid in the JWT header to a key in this array.

    accounts: list of ZoomAccount ORM objects (must have kid and private_key_path)
    Returns: {"keys": [...]} dict ready to be returned as JSON
    """
    keys = []

    for account in accounts:
        if not account.kid or not account.private_key_path:
            logger.warning(
                f"Account {account.account_id} missing kid or key path, skipping JWKS"
            )
            continue

        try:
            private_key = load_private_key(account.account_id)
            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            jwk = JsonWebKey.import_key( 
                public_pem, # type: ignore[arg-type]
                {"kty": "RSA", "use": "sig", "kid": account.kid}
            ) 
            keys.append(dict(jwk))

        except FileNotFoundError:
            logger.error(
                f"Private key not found for account {account.account_id} "
                f"at {account.private_key_path}"
            )
        except Exception as e:
            logger.error(
                f"Error loading key for account {account.account_id}: {e}"
            )

    return {"keys": keys}
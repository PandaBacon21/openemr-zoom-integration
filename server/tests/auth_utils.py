from datetime import datetime, timedelta, timezone

import jwt


TEST_JWT_SECRET = "test-config-jwt-secret-0123456789"


def make_auth_headers(secret: str = TEST_JWT_SECRET) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "admin",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


AUTH_HEADERS = make_auth_headers()
INVALID_AUTH_HEADERS = {"Authorization": "Bearer invalid-token"}

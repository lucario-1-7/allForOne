"""Password hashing and signed session tokens using only the standard library.

PBKDF2-HMAC-SHA256 for passwords, HMAC-signed "uid.expiry.signature" tokens for
sessions. No external crypto dependencies to keep the install simple.
"""

import hashlib
import hmac
import os
import time

from .config import SECRET_KEY, TOKEN_TTL_SECONDS

_PBKDF2_ITERATIONS = 300_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(user_id: int) -> str:
    expiry = int(time.time()) + TOKEN_TTL_SECONDS
    payload = f"{user_id}.{expiry}"
    return f"{payload}.{_sign(payload)}"


def verify_token(token: str) -> int | None:
    """Return the user id if the token is valid and unexpired, else None."""
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return None
    payload, signature = parts
    if not hmac.compare_digest(_sign(payload), signature):
        return None
    try:
        user_id_str, expiry_str = payload.split(".")
        if int(expiry_str) < time.time():
            return None
        return int(user_id_str)
    except ValueError:
        return None

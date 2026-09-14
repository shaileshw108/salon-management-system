import hashlib
import hmac
import secrets
import time

import jwt

from .config import get_settings


ALGORITHM = "HS256"
QUEUE_STATUS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt, expected = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {"sub": subject, "iat": now, "exp": now + settings.access_token_expire_minutes * 60}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        return str(subject) if subject else None
    except jwt.PyJWTError:
        return None


def create_queue_status_token(entry_id: int) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": f"queue:{entry_id}",
        "typ": "queue_status",
        "iat": now,
        "exp": now + QUEUE_STATUS_TOKEN_EXPIRE_HOURS * 60 * 60,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_queue_status_token(token: str) -> int | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("typ") != "queue_status":
            return None
        subject = str(payload.get("sub", ""))
        if not subject.startswith("queue:"):
            return None
        entry_id = int(subject.split(":", 1)[1])
        return entry_id if entry_id > 0 else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None

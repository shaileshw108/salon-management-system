from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from .config import get_settings

ALGORITHM = "HS256"


def issue_token(username: str) -> str:
    settings = get_settings()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": username, "exp": expiry}, settings.secret_key, algorithm=ALGORITHM)


def read_token(token: str) -> str:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise ValueError
        return username
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Invalid or expired token")

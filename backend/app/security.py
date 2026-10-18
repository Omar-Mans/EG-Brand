import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings

_ITER = 240_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITER)
    return f"pbkdf2_sha256${_ITER}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt_b64, digest_b64 = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(iters))
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False


def create_token(sub: str, *, purpose: str = "access", minutes: int | None = None, extra: dict | None = None) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "purpose": purpose, "iat": now, "exp": now + timedelta(minutes=minutes or s.jwt_expire_minutes)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_token(token: str, purpose: str = "access") -> dict:
    data = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    if data.get("purpose") != purpose:
        raise jwt.InvalidTokenError("wrong token purpose")
    return data


def _fernet() -> Fernet:
    s = get_settings()
    key = s.token_encryption_key
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(s.jwt_secret.encode()).digest()).decode()
    return Fernet(key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode() if value else ""


def decrypt(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return ""

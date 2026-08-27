"""Simple single-user password gate.

Not a full auth system (by design, per product decision): one shared password
protects the whole app. On successful login we issue a signed, expiring
session token (itsdangerous) stored in an HttpOnly cookie; every protected
route depends on `require_session`.
"""
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from fastapi import Cookie, HTTPException, status

from .config import get_settings

SESSION_COOKIE_NAME = "nadlan_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.session_secret, salt="nadlan-session")


def create_session_token() -> str:
    return _serializer().dumps({"authenticated": True})


def verify_password(password: str) -> bool:
    settings = get_settings()
    return password == settings.app_password


def require_session(nadlan_session: str | None = Cookie(default=None)) -> None:
    if not nadlan_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        _serializer().loads(nadlan_session, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

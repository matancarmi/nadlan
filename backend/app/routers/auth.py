from fastapi import APIRouter, HTTPException, Response, status

from ..config import get_settings
from ..schemas import LoginRequest
from ..security import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS, create_session_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    if not verify_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    settings = get_settings()
    token = create_session_token()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.session_cookie_secure,
        # Frontend and backend live on different subdomains in production, so the
        # cookie must be SameSite=None (requires Secure) to be sent cross-site.
        samesite="none" if settings.session_cookie_secure else "lax",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}

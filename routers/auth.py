import hashlib
import hmac
import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from config import VIDEOS_PIN, VIDEOS_SESSION_SECRET, VIDEOS_SESSION_MAX_AGE

router = APIRouter(tags=["auth"])

_attempts: dict[str, list[float]] = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW = 60


class PinRequest(BaseModel):
    pin: str


def _create_token() -> str:
    ts = str(int(time.time()))
    sig = hmac.new(
        VIDEOS_SESSION_SECRET.encode(), ts.encode(), hashlib.sha256
    ).hexdigest()[:16]
    return f"{ts}.{sig}"


def validate_session(token: str) -> bool:
    parts = token.split(".")
    if len(parts) != 2:
        return False
    ts, sig = parts
    expected = hmac.new(
        VIDEOS_SESSION_SECRET.encode(), ts.encode(), hashlib.sha256
    ).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        if int(ts) + VIDEOS_SESSION_MAX_AGE < time.time():
            return False
    except ValueError:
        return False
    return True


@router.post("/api/auth/verify-pin")
async def verify_pin(body: PinRequest, request: Request, response: Response):
    ip = request.client.host if request.client else "unknown"
    now = time.time()

    _attempts[ip] = [t for t in _attempts[ip] if now - t < WINDOW]
    if len(_attempts[ip]) >= MAX_ATTEMPTS:
        raise HTTPException(429, "Слишком много попыток. Подождите минуту.")

    _attempts[ip].append(now)

    if not hmac.compare_digest(body.pin, VIDEOS_PIN):
        raise HTTPException(401, "Invalid PIN")

    _attempts.pop(ip, None)
    token = _create_token()
    response.set_cookie(
        "viral_session",
        token,
        httponly=True,
        samesite="lax",
        max_age=VIDEOS_SESSION_MAX_AGE,
    )
    return {"ok": True}


@router.get("/api/auth/check")
async def check_auth(request: Request):
    token = request.cookies.get("viral_session")
    if token and validate_session(token):
        return {"authenticated": True}
    raise HTTPException(401, "Not authenticated")

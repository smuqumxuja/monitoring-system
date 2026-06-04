from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from jose import JWTError, jwt

from app.config import get_settings


CAPTCHA_EXPIRE_SECONDS = 300


def create_captcha() -> dict[str, str | int]:
    rng = secrets.SystemRandom()
    operator = rng.choice(["+", "-", "*"])
    left = rng.randint(2, 12)
    right = rng.randint(2, 12)

    if operator == "-":
        left, right = max(left, right), min(left, right)
        answer = left - right
    elif operator == "*":
        left = rng.randint(2, 9)
        right = rng.randint(2, 9)
        answer = left * right
    else:
        answer = left + right

    nonce = secrets.token_urlsafe(16)
    settings = get_settings()
    payload = {
        "sub": "captcha",
        "nonce": nonce,
        "answer_hash": _answer_hash(nonce, str(answer)),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=CAPTCHA_EXPIRE_SECONDS),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return {
        "captcha_token": token,
        "question": f"{left} {operator} {right} = ?",
        "expires_in_seconds": CAPTCHA_EXPIRE_SECONDS,
    }


def verify_captcha(token: str | None, answer: str | None) -> bool:
    if not token or not answer:
        return False
    try:
        normalized = str(int(answer.strip()))
    except ValueError:
        return False

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return False

    if payload.get("sub") != "captcha":
        return False
    nonce = payload.get("nonce")
    expected = payload.get("answer_hash")
    if not isinstance(nonce, str) or not isinstance(expected, str):
        return False
    return hmac.compare_digest(expected, _answer_hash(nonce, normalized))


def _answer_hash(nonce: str, answer: str) -> str:
    settings = get_settings()
    message = f"{nonce}:{answer}".encode("utf-8")
    return hmac.new(settings.secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()

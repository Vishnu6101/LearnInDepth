from datetime import timedelta, datetime, timezone
from jose import jwt
import secrets

SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY_MINUTES = 15

REFRESH_TOKEN_EXPIRY_DAYS = 7

def create_access_token(user_id: str, session_id: str) -> str:

    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES),
        "iat": datetime.now(timezone.utc)
    }

    return jwt.encode(payload, key=SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    return jwt.decode(token=token, key=SECRET_KEY, algorithms=[ALGORITHM])


def create_refresh_token():
    return secrets.token_urlsafe(32)

def refresh_token_expiry():
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
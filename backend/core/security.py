from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import bcrypt
from jose import JWTError, jwt

load_dotenv()

BCRYPT_MAX_PASSWORD_BYTES = 72


def is_valid_bcrypt_password(plain_password: str) -> bool:
    return len(plain_password.encode("utf-8")) <= BCRYPT_MAX_PASSWORD_BYTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not is_valid_bcrypt_password(plain_password):
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False


def hash_password(plain_password: str) -> str:
    if not is_valid_bcrypt_password(plain_password):
        raise ValueError("Password cannot be longer than 72 bytes")
    return bcrypt.hashpw(
        plain_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


def _get_secret_key() -> str:
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")
    return SECRET_KEY


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "sub": subject,
        "exp": expire,
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            return None
        return str(subject)
    except JWTError:
        return None

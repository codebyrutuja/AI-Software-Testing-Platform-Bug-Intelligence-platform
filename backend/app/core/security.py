"""
app/core/security.py
─────────────────────
PURPOSE:
  All security-related functions in one place:
  - Password hashing and verification (using bcrypt via passlib)
  - JWT access token creation and decoding
  - Refresh token creation

WHY HASH PASSWORDS?
  If the database is compromised, hashed passwords cannot be reversed
  to plain text (with a good algorithm). bcrypt is intentionally slow,
  making brute-force attacks impractical.

WHY JWT?
  JWT (JSON Web Token) is a self-contained token. The backend can verify
  it without looking up the database on every request. The token contains
  the user's ID and expiry time, signed with a secret key.

TOKEN STRUCTURE:
  header.payload.signature
  - Header: algorithm used (HS256)
  - Payload: user data (sub=user_id, exp=expiry)
  - Signature: cryptographic proof it wasn't tampered with
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# ── Password Hashing ────────────────────────────────────────────────────────────
def hash_password(plain_password: str) -> str:
    """
    Converts a plain text password into a bcrypt hash.
    Direct bcrypt avoids passlib-bcrypt 4.x compatibility issues on Python 3.13.
    """
    pwd_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks if a plain password matches a stored hash.
    Returns True if they match, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ── JWT Token Creation ──────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token with an expiry time.

    Args:
        data: Dictionary of claims to include (e.g., {"sub": "user-uuid"})
        expires_delta: How long the token is valid (default: from settings)

    Returns:
        A signed JWT string to be sent to the client.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "type": "access",  # Distinguish access from refresh tokens
    })

    # jwt.encode signs the payload with our SECRET_KEY
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Creates a longer-lived refresh token.
    Used to get a new access token when it expires without re-logging in.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({
        "exp": expire,
        "type": "refresh",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decodes and validates a JWT token.

    Returns the payload dict if valid, None if invalid/expired.

    This validates:
    - The signature (was it signed by us?)
    - The expiry (has it expired?)
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


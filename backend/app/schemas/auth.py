"""
app/schemas/auth.py
────────────────────
PURPOSE:
  Pydantic schemas specifically for authentication flows.
  Separate from user schemas to keep concerns clean. use while login
"""

from pydantic import BaseModel, EmailStr, Field


# ── Login Input ───────────────────────────────────────────────────────────────────
# Used by: POST /auth/login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


# ── Token Response ────────────────────────────────────────────────────────────────
# Returned after successful login or token refresh.
# access_token  → short-lived (30 min), used for every API call
# refresh_token → long-lived (7 days), used ONLY to get a new access_token
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"       # OAuth2 standard value
    expires_in: int                  # Seconds until access_token expires


# ── Refresh Token Input ───────────────────────────────────────────────────────────
# Used by: POST /auth/refresh
class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)

import os
import secrets
from datetime import timedelta
from typing import List, Optional

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db, utcnow
import models

# Secret key configuration (fail-fast: never fall back to a hardcoded key)
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
RESET_TOKEN_EXPIRE_HOURS = 2

# ============================================================
# OAuth Provider Credentials (Google & LinkedIn)
# ============================================================
# These are read from environment variables / .env file.
# They MUST be configured before OAuth login flows can verify
# tokens against the respective identity providers.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")

# ============================================================
# LinkedIn OAuth / OpenID Connect configuration
# ============================================================
# LinkedIn retired the legacy r_* profile/email scopes — requesting them
# now returns ``invalid_scope_error``. The only valid scopes are the
# OIDC-standard:
#   openid profile email
#
# The token-verification side (verify_oauth_token below) already uses
# https://api.linkedin.com/v2/userinfo, which is exactly the endpoint
# these OIDC scopes grant access to — so scope and verification are now
# consistent with each other.
LINKEDIN_SCOPE = os.getenv("LINKEDIN_SCOPE", "openid profile email")
LINKEDIN_AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

# Map provider identifiers to the environment-configured credentials
OAUTH_PROVIDERS = {
    "google": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
    },
    "linkedin": {
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
        "scope": LINKEDIN_SCOPE,
        "authorization_url": LINKEDIN_AUTHORIZATION_URL,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
    },
}


def get_linkedin_authorization_url(
    state: Optional[str] = None, redirect_uri: Optional[str] = None
) -> dict:
    """
    Build the LinkedIn OAuth 2.0 / OIDC authorization URL using the
    modern ``openid profile email`` scopes (the retired legacy r_* scopes
    trigger LinkedIn's invalid_scope_error).

    Returns a dict with the ``authorization_url`` and the ``state`` value
    (auto-generated with a CSPRNG when not supplied) so callers can send
    the user to LinkedIn and verify the state on the callback.
    """
    from urllib.parse import quote, urlencode

    if state is None:
        state = secrets.token_urlsafe(24)
    if not redirect_uri:
        redirect_uri = LINKEDIN_REDIRECT_URI
    if not redirect_uri:
        raise ValueError(
            "LINKEDIN_REDIRECT_URI environment variable is not set — "
            "it must match a redirect URL whitelisted in the LinkedIn app settings"
        )

    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": LINKEDIN_SCOPE,
    }
    url = f"{LINKEDIN_AUTHORIZATION_URL}?{urlencode(params, quote_via=quote)}"
    return {"authorization_url": url, "state": state}


def verify_oauth_token(provider: str, token: str) -> dict:
    """
    Verifies an OAuth token against the respective identity provider
    (Google or LinkedIn) and returns the verified user information
    containing ``email``, ``name``, and ``avatar_url``.

    The verification uses the provider credentials (``*_CLIENT_ID`` /
    ``*_CLIENT_SECRET``) read from the environment so that only tokens
    issued for *this* application are accepted.

    Raises ``HTTPException`` (401) when the token is invalid or was not
    issued for this application.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth token is required for token verification",
        )

    provider_key = (provider or "").lower()
    if provider_key not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    config = OAUTH_PROVIDERS[provider_key]

    import httpx

    try:
        if provider_key == "google":
            # Google: verify the ID token via the tokeninfo endpoint.
            resp = httpx.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": token},
                timeout=10.0,
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google OAuth token verification failed: token is invalid or expired",
                )
            data = resp.json()
            # Verify that the token was issued for our Google client ID.
            if config["client_id"] and data.get("aud") != config["client_id"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google OAuth token was not issued for this application",
                )
            return {
                "email": data.get("email"),
                "name": data.get("name"),
                "avatar_url": data.get("picture"),
            }

        elif provider_key == "linkedin":
            # LinkedIn: use the OIDC userinfo endpoint with the bearer token.
            resp = httpx.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="LinkedIn OAuth token verification failed: token is invalid or expired",
                )
            data = resp.json()
            # Optionally verify the token client_id if present in the response.
            token_client_id = data.get("cid") or data.get("aud")
            if config["client_id"] and token_client_id and token_client_id != config["client_id"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="LinkedIn OAuth token was not issued for this application",
                )
            return {
                "email": data.get("email"),
                "name": data.get("name"),
                "avatar_url": data.get("picture"),
            }

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"{provider.capitalize()} OAuth verification timed out",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach {provider.capitalize()} OAuth provider for token verification",
        )

    # Should never reach here
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Could not verify {provider.capitalize()} OAuth token",
    )

# bcrypt / passlib compatibility
if not hasattr(bcrypt, "__about__"):
    import types
    bcrypt.__about__ = types.ModuleType("bcrypt.__about__")
    try:
        bcrypt.__about__.__version__ = bcrypt.__version__
    except AttributeError:
        bcrypt.__about__.__version__ = "0.0.0"

BCRYPT_MAX_BYTES = 72


def _truncate_password(password: str) -> bytes:
    """Encode the password to UTF-8 and truncate to bcrypt's 72-byte limit."""
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(_truncate_password(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Defensive against bad rows in the database: if the stored value is
    missing, not a bcrypt hash (e.g. plaintext or another scheme), or
    corrupted, we return False so /auth/login responds with a clean 401
    instead of crashing with a 500.
    """
    if not plain_password or not hashed_password:
        return False
    if not isinstance(hashed_password, str):
        hashed_password = str(hashed_password)
    if not hashed_password.startswith("$2"):
        # Not a bcrypt hash — cannot verify with pwd_context.
        return False
    try:
        return pwd_context.verify(_truncate_password(plain_password), hashed_password)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_roles(allowed_roles: List[str]):
    """
    Dependency factory to enforce role-based access control (RBAC).
    Usage: Depends(require_roles(["admin", "instructor"]))
    """
    def role_checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of roles [{', '.join(allowed_roles)}]",
            )
        return current_user
    return role_checker


# Quick role shorthands
require_admin = require_roles(["admin"])
require_instructor_or_admin = require_roles(["instructor", "admin"])


def require_role(*allowed_roles: str):
    """
    General-purpose role verification dependency.

    Usage (FastAPI):
        @router.get("/admin-only")
        def admin_only(current_user: models.User = Depends(require_role("admin"))):
            ...

        @router.get("/staff")
        def staff_only(current_user: models.User = Depends(require_role("admin", "instructor"))):
            ...

    Semantically equivalent to ``require_roles(list(allowed_roles))`` —
    provided as a friendlier, more explicit alias.
    """
    return require_roles(list(allowed_roles))


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def record_audit_log(
    db: Session,
    action: str,
    resource: str,
    details: Optional[str] = None,
    user: Optional[models.User] = None,
    ip_address: Optional[str] = None,
):
    """
    Helper function to record audit log events across any router.
    """
    log_entry = models.AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_address,
        timestamp=utcnow(),
    )
    db.add(log_entry)
    db.commit()


def create_password_reset_token(db: Session, user: models.User) -> str:
    """
    Generates a secure password reset token and stores it in the database with an expiration date.
    """
    token = secrets.token_urlsafe(32)
    expires_at = utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
    
    # Invalidate existing unused tokens for this user
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.used == False,
    ).update({"used": True})

    reset_record = models.PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_record)
    db.commit()
    return token


def verify_password_reset_token(db: Session, token: str) -> Optional[models.User]:
    """
    Validates a password reset token and returns the corresponding User if valid and unexpired.
    """
    record = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token == token,
            models.PasswordResetToken.used == False,
            models.PasswordResetToken.expires_at > utcnow(),
        )
        .first()
    )
    if not record:
        return None
    
    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    return user
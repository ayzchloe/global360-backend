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

# Secret key configuration
SECRET_KEY = os.getenv("SECRET_KEY", "1955616771a8bfc4bb317dd5ad05f3f78435a510a66fe106a465c00eead7be2c")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
RESET_TOKEN_EXPIRE_HOURS = 2

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
    return pwd_context.verify(_truncate_password(plain_password), hashed_password)


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
import os
from datetime import datetime, timedelta

import bcrypt  # imported early for the __about__ workaround below
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
import models

# Secret key now comes from the environment (.env locally, Render env vars in production)
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# ---------------------------------------------------------------------------
# bcrypt / passlib 1.7.4 compatibility
# ---------------------------------------------------------------------------
# ``passlib`` 1.7.4 detects the bcrypt version by reading
# ``bcrypt.__about__.__version__``.  That attribute is present in bcrypt 4.0.x
# but is absent (or relocated) in some later 4.x releases, surfacing as:
#
#     (trapped) error reading bcrypt version ...
#     AttributeError: module 'bcrypt' has no attribute '__about__'
#
# We pin ``bcrypt==4.0.1`` (see requirements.txt) which keeps the attribute
# available, but we also install a defensive fallback here so the code stays
# resilient even if a newer bcrypt is installed later.
if not hasattr(bcrypt, "__about__"):
    import types

    bcrypt.__about__ = types.ModuleType("bcrypt.__about__")
    try:
        bcrypt.__about__.__version__ = bcrypt.__version__
    except AttributeError:
        bcrypt.__about__.__version__ = "0.0.0"

# bcrypt only ever uses the first 72 bytes of a password.  bcrypt >= 4.1
# raises ``ValueError: password cannot be longer than 72 bytes, truncate
# manually if necessary`` instead of silently truncating, so we truncate
# explicitly to remain compatible with every bcrypt version.
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


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
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
    if user is None:
        raise credentials_exception
    return user
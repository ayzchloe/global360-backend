from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.Token, status_code=201)
def register(user_in: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = user_in.role if user_in.role in ("student", "instructor", "admin") else "student"
    new_user = models.User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=auth.hash_password(user_in.password),
        role=role,
        phone=user_in.phone,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # If student, automatically instantiate corresponding Student record
    if new_user.role == "student":
        student_profile = models.Student(
            user_id=new_user.id,
            enrollment_no=f"G360-{new_user.id:04d}",
            program="General Studies",
            status="active",
        )
        db.add(student_profile)
        db.commit()

    # Log audit event
    auth.record_audit_log(
        db=db,
        action="REGISTER",
        resource="User",
        details=f"New user registered: {new_user.email} with role {new_user.role}",
        user=new_user,
        ip_address=auth.get_client_ip(request),
    )

    token = auth.create_access_token(data={"sub": str(new_user.id), "role": new_user.role})
    return {"access_token": token, "user": new_user}


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Accepts a JSON body: { "email": "...", "password": "..." } (schemas.LoginRequest).
    # Email lookup is case-insensitive so "Admin@Global360.edu" matches a row
    # stored as "admin@global360.edu" instead of failing with 401.
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == credentials.email.lower())
        .first()
    )
    if not user or not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Audit log
    auth.record_audit_log(
        db=db,
        action="LOGIN",
        resource="User",
        details=f"User logged in: {user.email}",
        user=user,
        ip_address=auth.get_client_ip(request),
    )

    token = auth.create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": token, "user": user}


@router.get("/user", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.put("/user", response_model=schemas.UserOut)
def update_profile(
    profile_data: schemas.UserProfileUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if profile_data.name is not None:
        current_user.name = profile_data.name
    if profile_data.phone is not None:
        current_user.phone = profile_data.phone
    if profile_data.bio is not None:
        current_user.bio = profile_data.bio
    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url

    db.commit()
    db.refresh(current_user)
    return current_user


# ============================================================
# OAUTH (Google & LinkedIn Support)
# ============================================================

def handle_oauth(req: schemas.OAuthLoginRequest, provider: str, request: Request, db: Session):
    email = req.email
    name = req.name or (email.split("@")[0].capitalize() if email else f"{provider.capitalize()} User")
    avatar_url = req.avatar_url

    # If an OAuth token is provided, verify it against the identity provider
    # using the credentials read from environment variables. The verified
    # values from the provider take precedence over the request payload.
    if req.token:
        verified = auth.verify_oauth_token(provider, req.token)
        if verified.get("email"):
            email = verified["email"]
        if verified.get("name"):
            name = verified["name"]
        if verified.get("avatar_url"):
            avatar_url = verified["avatar_url"]

    if not email:
        raise HTTPException(status_code=400, detail="Email is required for OAuth login")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Auto-create user from OAuth provider
        random_pwd = auth.secrets.token_urlsafe(16)
        user = models.User(
            name=name,
            email=email,
            hashed_password=auth.hash_password(random_pwd),
            role="student",
            avatar_url=avatar_url,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Auto-create student profile
        student_profile = models.Student(
            user_id=user.id,
            enrollment_no=f"G360-{user.id:04d}",
            program="General Studies",
            status="active",
        )
        db.add(student_profile)
        db.commit()

        auth.record_audit_log(
            db=db,
            action="OAUTH_REGISTER",
            resource="User",
            details=f"User signed up via {provider}: {user.email}",
            user=user,
            ip_address=auth.get_client_ip(request),
        )
    else:
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            db.commit()

    token = auth.create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": token, "user": user}


@router.post("/oauth/google", response_model=schemas.Token)
@router.post("/google", response_model=schemas.Token)
def oauth_google(req: schemas.OAuthLoginRequest, request: Request, db: Session = Depends(get_db)):
    return handle_oauth(req, provider="Google", request=request, db=db)


@router.post("/oauth/linkedin", response_model=schemas.Token)
@router.post("/linkedin", response_model=schemas.Token)
def oauth_linkedin(req: schemas.OAuthLoginRequest, request: Request, db: Session = Depends(get_db)):
    return handle_oauth(req, provider="LinkedIn", request=request, db=db)


# ============================================================
# FORGOT & RESET PASSWORD
# ============================================================

@router.post("/forgot-password")
def forgot_password(
    req: schemas.ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user:
        # Always return 200 to prevent email enumeration, but give helpful dev note
        return {
            "message": "If that email is registered, password reset instructions have been generated.",
            "reset_token": None,
        }

    token = auth.create_password_reset_token(db=db, user=user)
    auth.record_audit_log(
        db=db,
        action="FORGOT_PASSWORD",
        resource="User",
        details=f"Password reset token requested for {user.email}",
        user=user,
        ip_address=auth.get_client_ip(request),
    )

    return {
        "message": "Password reset token generated successfully. In production this is emailed to the user.",
        "reset_token": token,
        "instructions": "Send POST /auth/reset-password with this token and your new_password.",
    }


@router.post("/reset-password")
def reset_password(
    req: schemas.ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth.verify_password_reset_token(db=db, token=req.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = auth.hash_password(req.new_password)
    
    # Mark token used
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == req.token
    ).update({"used": True})

    db.commit()

    auth.record_audit_log(
        db=db,
        action="RESET_PASSWORD",
        resource="User",
        details=f"Password successfully reset for {user.email}",
        user=user,
        ip_address=auth.get_client_ip(request),
    )

    return {"message": "Password reset successfully. You can now log in with your new password."}
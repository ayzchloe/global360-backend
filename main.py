from dotenv import load_dotenv
load_dotenv()

import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import models
from database import engine, SessionLocal
from routers import (
    auth_routes,
    students,
    courses,
    enrollments,
    assignments,
    instructor,
    sessions,
    certificates,
    finance,
    partnerships,
    contact,
    notifications,
    admin,
    blog,
    uploads,
    applications,
)


# Ensure static directories exist
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


def seed_default_accounts() -> None:
    """
    Idempotent startup seeding of default admin & instructor accounts.

    These credentials are for development/staging only. They use the same
    bcrypt-hashing path as the rest of the application (auth.hash_password),
    so the accounts can be used with the standard /auth/login flow.

    Production deployments should override these via environment variables
    (see .env.example) or remove this call entirely after first bootstrap.
    """
    import auth

    defaults = [
        {
            "name": os.getenv("DEFAULT_ADMIN_NAME", "Global360 Administrator"),
            "email": os.getenv("DEFAULT_ADMIN_EMAIL", "admin@global360.edu"),
            "password": os.getenv("DEFAULT_ADMIN_PASSWORD", "AdminPass123!"),
            "role": "admin",
            "phone": "+1 (555) 019-2831",
        },
        {
            "name": os.getenv("DEFAULT_INSTRUCTOR_NAME", "Prof. Marcus Vance"),
            "email": os.getenv("DEFAULT_INSTRUCTOR_EMAIL", "instructor@global360.edu"),
            "password": os.getenv("DEFAULT_INSTRUCTOR_PASSWORD", "InstructorPass123!"),
            "role": "instructor",
            "phone": "+1 (555) 019-4822",
        },
    ]

    db = SessionLocal()
    try:
        for creds in defaults:
            existing = db.query(models.User).filter(models.User.email == creds["email"]).first()
            if existing:
                continue
            user = models.User(
                name=creds["name"],
                email=creds["email"],
                hashed_password=auth.hash_password(creds["password"]),
                role=creds["role"],
                phone=creds.get("phone"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[seed] Created default {creds['role']} account: {creds['email']}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_payment_accounts() -> None:
    """
    Ensures default company bank details are seeded into the finance database.
    """
    db = SessionLocal()
    try:
        # Check if payment accounts table/model exists
        if hasattr(models, "PaymentAccount"):
            default_account_number = os.getenv(
                "DEFAULT_ACCOUNT_NUMBER", "11530112223716"
            )
            existing = db.query(models.PaymentAccount).filter_by(
                account_number=default_account_number
            ).first()
            if not existing:
                account = models.PaymentAccount(
                    bank_name=os.getenv("DEFAULT_BANK_NAME", "Meezan Bank (Askari IX Lahore Branch)"),
                    account_title=os.getenv("DEFAULT_ACCOUNT_TITLE", "KIRAN FATIMA"),
                    account_number=default_account_number,
                    iban=os.getenv("DEFAULT_IBAN", "PK34MEZN0011530112223716"),
                    is_active=True
                )
                db.add(account)
                db.commit()
                print("[seed] Default Meezan Bank payment account created.")
    except Exception as e:
        db.rollback()
        print(f"[seed warning] Payment account seeding skipped/failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown management.
    Ensures all database tables and indexes are initialized,
    then seeds default admin/instructor accounts and payment accounts if missing.
    """
    models.Base.metadata.create_all(bind=engine)
    seed_default_accounts()
    seed_payment_accounts()
    yield


app = FastAPI(
    title="Global360 API",
    description="Full-stack LMS, Student Portal, Instructor Workspace, Finance & Certification API for Global360.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Static file serving for uploaded files and assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# CORS Configuration — allow all origins, methods, and headers so the
# frontend can call the API from anywhere without CORS policy errors.
# Note: Starlette's CORSMiddleware echoes the request's Origin header when
# allow_credentials=True, so credentialed requests still work correctly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Global exception handler for unhandled errors.
#
# Without this, an unhandled exception is caught by Starlette's
# ServerErrorMiddleware, which sits OUTSIDE the CORS middleware stack, so the
# plain-text "Internal Server Error" response never receives CORS headers and
# the browser reports a CORS failure instead of the real 500.
# Registering a handler for `Exception` moves handling inside the middleware
# stack (ExceptionMiddleware), and we also set the CORS headers explicitly so
# frontend clients always receive a readable JSON 500.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the full traceback server-side so the real error is visible in logs.
    traceback.print_exception(type(exc), exc, exc.__traceback__)

    headers: dict[str, str] = {}
    origin = request.headers.get("origin")
    if origin:
        # Mirror CORSMiddleware behaviour (allow_origins=["*"] +
        # allow_credentials=True echoes the request's Origin header).
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
        headers=headers,
    )

# Router Registrations
app.include_router(auth_routes.router)
app.include_router(students.router)
app.include_router(courses.router)
app.include_router(enrollments.router)
app.include_router(assignments.router)
app.include_router(instructor.router)
app.include_router(sessions.router)
app.include_router(certificates.router)
app.include_router(finance.router)
app.include_router(partnerships.router)
app.include_router(contact.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(blog.router)
app.include_router(uploads.router)
app.include_router(applications.router)


@app.get("/", tags=["Health"])
def root():
    """
    Root system health check.
    """
    return {
        "status": "online",
        "service": "Global360 API v2.0",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth",
            "students": "/students",
            "courses": "/courses",
            "enrollments": "/enrollments",
            "assignments": "/assignments",
            "instructor": "/instructor",
            "sessions": "/sessions",
            "certificates": "/certificates",
            "fee_challans": "/fee-challans",
            "payment_accounts": "/payment-accounts",
            "partnerships": "/partnerships",
            "contact": "/contact",
            "notifications": "/notifications",
            "admin": "/admin",
            "blog": "/blog",
            "uploads": "/uploads",
            "applications": "/applications",
        },
    }
from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import models
from database import engine
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown management.
    Ensures all database tables and indexes are initialized.
    """
    models.Base.metadata.create_all(bind=engine)
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

# CORS Configuration
allowed_origins_env = os.getenv(
    "ALLOWED_ORIGINS",
    "https://global360-zeta.vercel.app,http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
)
origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
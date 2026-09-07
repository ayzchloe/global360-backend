from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine
from routers import auth_routes, students, certificates, applications


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Ensures database tables are created before the app starts accepting requests.
    """
    # Create database tables if they do not exist
    models.Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Global360 API",
    description="Backend REST API for Global360 student records, authentication, and certificate verification.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
# Pulls allowed origins from environment variable if set, otherwise falls back to defaults
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "https://global360-zeta.vercel.app,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route Handlers
app.include_router(auth_routes.router)
app.include_router(students.router)
app.include_router(certificates.router)
app.include_router(applications.router)


@app.get("/", tags=["Health"])
def root():
    """
    Root health check endpoint.
    """
    return {
        "status": "running",
        "service": "Global360 API",
        "docs": "/docs"
    }
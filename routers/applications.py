import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/applications", tags=["applications"])

# Default password assigned to newly provisioned student accounts on approval.
# Override via environment (Render -> Environment) if a different default is needed.
DEFAULT_STUDENT_PASSWORD = os.getenv("APPROVAL_DEFAULT_PASSWORD", "Global360@2026")

APPROVED_STATUS = "APPROVED"


def provision_student_records(db: Session, app_record: models.Application) -> dict:
    """
    Idempotently provision the linked User, Student and Enrollment records for
    an approved admissions application.

    Each step is skipped when the record already exists, so this is safe to
    call repeatedly (e.g. on re-approval or during a backfill). It only
    ``flush()`` es to obtain generated primary keys — the caller owns the
    surrounding transaction and decides when to ``commit()``.

    Returns a summary dict indicating which records were newly created:
    ``{"user": User|None, "student": Student|None, "enrollment": Enrollment|None}``
    """
    result: dict = {"user": None, "student": None, "enrollment": None}

    # 1) User — match email case-insensitively
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == func.lower(app_record.email))
        .first()
    )
    if not user:
        user = models.User(
            name=app_record.full_name,
            email=app_record.email.lower(),
            hashed_password=auth.hash_password(DEFAULT_STUDENT_PASSWORD),
            role="student",
        )
        db.add(user)
        db.flush()  # populate user.id before creating the Student profile
        result["user"] = user

    # 2) Student profile — one per user (user_id is unique)
    student = (
        db.query(models.Student)
        .filter(models.Student.user_id == user.id)
        .first()
    )
    if not student:
        student = models.Student(
            user_id=user.id,
            enrollment_no=f"G360-{user.id:04d}",
            program=app_record.track or "General Studies",
            status="active",
        )
        db.add(student)
        db.flush()  # populate student.id before creating the Enrollment
        result["student"] = student

    # 3) Enrollment — resolve the course from the application's requested track
    course = None
    if app_record.track:
        course = (
            db.query(models.Course)
            .filter(func.lower(models.Course.track) == func.lower(app_record.track))
            .first()
        )
    if course:
        enrollment = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.student_id == student.id,
                models.Enrollment.course_id == course.id,
            )
            .first()
        )
        if not enrollment:
            enrollment = models.Enrollment(
                student_id=student.id,
                course_id=course.id,
                status="active",
            )
            db.add(enrollment)
            db.flush()
            result["enrollment"] = enrollment

    return result


def provision_summary(provisioned: dict) -> dict:
    """Serialize a provisioning result into a plain (JSON-safe) report."""
    return {
        "user_created": provisioned["user"] is not None,
        "student_created": provisioned["student"] is not None,
        "enrollment_created": provisioned["enrollment"] is not None,
    }


# PUBLIC — matches the "Apply Now" button on /admissions and all program pages
@router.post("/", response_model=schemas.ApplicationOut, status_code=201)
def submit_application(app_in: schemas.ApplicationCreate, db: Session = Depends(get_db)):
    new_app = models.Application(**app_in.dict())
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    return new_app


# ADMIN-ONLY — view submitted admissions applications
@router.get("/", response_model=list[schemas.ApplicationOut])
def list_applications(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    query = db.query(models.Application)
    if status_filter:
        query = query.filter(models.Application.status == status_filter)
    return query.order_by(models.Application.submitted_at.desc()).all()


# ADMIN-ONLY — approve an application AND atomically provision the linked
# User / Student / Enrollment records in a single database transaction.
@router.post("/{app_id}/approve", response_model=schemas.ApplicationOut)
def approve_application(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    app_record = db.query(models.Application).filter(models.Application.id == app_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    # a) Update application status
    app_record.status = APPROVED_STATUS

    try:
        # b/c/d) Provision User -> Student -> Enrollment (idempotent, flushed)
        provision_student_records(db, app_record)
        # e) Single atomic commit — either everything persists or nothing does
        db.commit()
    except Exception as exc:  # noqa: BLE001 — any failure must roll the whole approval back
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Approval failed and was rolled back: {exc}",
        )

    db.refresh(app_record)
    return app_record


# ADMIN-ONLY — update status of admissions application (accept/reject).
# Setting the status to "approved" (case-insensitive) triggers the same atomic
# User/Student/Enrollment provisioning as the /approve endpoint.
@router.patch("/{app_id}/status", response_model=schemas.ApplicationOut)
def update_application_status(
    app_id: int,
    status_value: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    app_record = db.query(models.Application).filter(models.Application.id == app_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    app_record.status = status_value

    try:
        if status_value.strip().lower() == "approved":
            provision_student_records(db, app_record)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Status update failed and was rolled back: {exc}",
        )

    db.refresh(app_record)
    return app_record


# ADMIN-ONLY — one-click fix for legacy approved applications that are missing
# their User / Student / Enrollment records (e.g. Daman Zahra). Safe to run any
# time: every step is idempotent and each application is committed separately
# so one bad row cannot abort the whole backfill.
@router.post("/backfill-approved")
def backfill_approved_applications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    legacy_apps = (
        db.query(models.Application)
        .filter(func.lower(models.Application.status) == "approved")
        .all()
    )
    report = []
    for app_record in legacy_apps:
        try:
            provisioned = provision_student_records(db, app_record)
            db.commit()
            report.append(
                {
                    "application_id": app_record.id,
                    "full_name": app_record.full_name,
                    "email": app_record.email,
                    **provision_summary(provisioned),
                }
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            report.append(
                {
                    "application_id": app_record.id,
                    "full_name": app_record.full_name,
                    "email": app_record.email,
                    "error": str(exc),
                }
            )
    return {"processed": len(report), "details": report}


# PUBLIC — matches the newsletter box on the Blog and Footer
@router.post("/newsletter", status_code=201)
def subscribe_newsletter(sub: schemas.NewsletterCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.NewsletterSubscriber)
        .filter(models.NewsletterSubscriber.email == sub.email)
        .first()
    )
    if existing:
        return {"message": "Already subscribed to Global360 Newsletter"}

    new_sub = models.NewsletterSubscriber(email=sub.email)
    db.add(new_sub)
    db.commit()
    return {"message": "Subscribed successfully"}
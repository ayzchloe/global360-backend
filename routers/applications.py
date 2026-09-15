import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

logger = logging.getLogger("global360.applications")

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

    Returns a dict with the final records (even if they already existed) and
    which ones were newly created:
    ``{"user": User, "student": Student, "enrollment": Enrollment|None,
       "user_created": bool, "student_created": bool, "enrollment_created": bool}``
    """
    result: dict = {
        "user": None,
        "student": None,
        "enrollment": None,
        "user_created": False,
        "student_created": False,
        "enrollment_created": False,
    }

    # 1) User — match email case-insensitively
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == func.lower(app_record.email))
        .first()
    )
    if not user:
        # Prefer the password the applicant chose at submission time (already
        # bcrypt-hashed in applications.hashed_password — do NOT re-hash it).
        # Legacy applications submitted without a password fall back to the
        # shared default.
        hashed_password = (
            app_record.hashed_password
            or auth.hash_password(DEFAULT_STUDENT_PASSWORD)
        )
        user = models.User(
            name=app_record.full_name,
            email=app_record.email.lower(),
            hashed_password=hashed_password,
            role="student",
        )
        db.add(user)
        db.flush()  # populate user.id before creating the Student profile
        result["user"] = user
        result["user_created"] = True

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
        result["student_created"] = True

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
            result["enrollment_created"] = True

    return result


def provision_summary(provisioned: dict) -> dict:
    """Serialize a provisioning result into a plain (JSON-safe) report."""
    return {
        "user_created": provisioned["user_created"],
        "student_created": provisioned["student_created"],
        "enrollment_created": provisioned["enrollment_created"],
    }


# PUBLIC — matches the "Apply Now" button on /admissions and all program pages
@router.post("/", response_model=schemas.ApplicationOut, status_code=201)
def submit_application(app_in: schemas.ApplicationCreate, db: Session = Depends(get_db)):
    # Hash the applicant's chosen password (when provided) BEFORE it reaches
    # the database — the plaintext is never persisted. The stored hash is
    # reused to create the User account when the application is approved.
    app_data = app_in.dict()
    chosen_password = app_data.pop("password", None)

    new_app = models.Application(
        **app_data,
        hashed_password=auth.hash_password(chosen_password) if chosen_password else None,
    )
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
@router.post("/{app_id}/approve")
def approve_application(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """
    Approves an admissions application and transactionally auto-enrolls the
    applicant. Within ONE session/transaction (flush, then commit):

      a) Application.status -> APPROVED
      b) User  (created if no user exists with the application's email)
      c) Student (created if missing for the user, status='active',
         enrollment number + program from the application data)
      d) Enrollment (created if missing for student_id + course_id,
         status='active' — compared case-insensitively everywhere)
      e) db.commit() — either all writes persist or nothing does.

    Returns a JSON confirmation of the application, the Student record and
    the Enrollment record (with *_created flags for each).
    """
    app_record = db.query(models.Application).filter(models.Application.id == app_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found")

    # a) Update application status
    app_record.status = APPROVED_STATUS

    try:
        # b/c/d) Provision User -> Student -> Enrollment (idempotent, flushed)
        provisioned = provision_student_records(db, app_record)
        # e) Single atomic commit — either everything persists or nothing does
        db.commit()
    except Exception as exc:  # noqa: BLE001 — any failure must roll the whole approval back
        db.rollback()
        logger.error("Approval failed for application %s, transaction rolled back: %s", app_id, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Approval failed and was rolled back: {exc}",
        )

    db.refresh(app_record)
    student = provisioned["student"]
    enrollment = provisioned["enrollment"]

    logger.info(
        "Application %s approved: student_created=%s, enrollment_created=%s",
        app_id,
        provisioned["student_created"],
        provisioned["enrollment_created"],
    )

    # Clear confirmation of both writes (student + enrollment)
    # Top-level email/user_id let the frontend redirect the admin or notify
    # the student without digging through nested objects.
    return {
        "message": "Application approved. Student profile and course enrollment provisioned.",
        "email": app_record.email,
        "user_id": student.user_id if student else None,
        "application": {
            "id": app_record.id,
            "full_name": app_record.full_name,
            "email": app_record.email,
            "track": app_record.track,
            "status": app_record.status,
        },
        "user_created": provisioned["user_created"],
        "student_created": provisioned["student_created"],
        "enrollment_created": provisioned["enrollment_created"],
        "student": {
            "id": student.id,
            "user_id": student.user_id,
            "enrollment_no": student.enrollment_no,
            "program": student.program,
            "status": student.status,
        } if student else None,
        "enrollment": {
            "id": enrollment.id,
            "student_id": enrollment.student_id,
            "course_id": enrollment.course_id,
            "status": enrollment.status,
        } if enrollment else None,
        "enrollment_note": (
            None
            if enrollment
            else "No course matched the application track — student profile was "
            "created, but no enrollment row was inserted. Enroll manually or "
            "re-check the course 'track' value."
        ),
    }


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
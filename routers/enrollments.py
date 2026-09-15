from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from database import get_db, utcnow
import models
import schemas
import auth

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.post("/", response_model=schemas.EnrollmentOut, status_code=201)
def enroll(
    enrollment_in: schemas.EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    student = db.query(models.Student).filter(models.Student.id == enrollment_in.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    course = db.query(models.Course).filter(models.Course.id == enrollment_in.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == enrollment_in.student_id,
            models.Enrollment.course_id == enrollment_in.course_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")

    new_enrollment = models.Enrollment(
        student_id=enrollment_in.student_id,
        course_id=enrollment_in.course_id,
        status="active",
        progress_percentage=0.0,
        enrolled_at=utcnow(),
    )
    db.add(new_enrollment)
    db.commit()
    db.refresh(new_enrollment)
    return new_enrollment


@router.get("/", response_model=list[schemas.EnrollmentDetailOut])
def list_all_enrollments(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Backs the /portal/admin enrollments overview.
    """
    # joinedload: fetch each enrollment's course in a single query so
    # response serialization never triggers per-row lazy loads (and one
    # missing course can't crash the whole listing).
    query = db.query(models.Enrollment).options(joinedload(models.Enrollment.course))
    if status_filter:
        # Case-insensitive so 'ACTIVE', 'Active' and 'active' all match
        query = query.filter(func.lower(models.Enrollment.status) == status_filter.strip().lower())
    return query.order_by(models.Enrollment.enrolled_at.desc()).all()


@router.get("/student/{student_id}", response_model=list[schemas.EnrollmentDetailOut])
def get_student_enrollments(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Required for /portal/dashboard to render 'enrolled courses'.
    """
    return (
        db.query(models.Enrollment)
        .options(joinedload(models.Enrollment.course))
        .filter(models.Enrollment.student_id == student_id)
        .all()
    )


@router.get("/{enrollment_id}", response_model=schemas.EnrollmentDetailOut)
def get_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    enrollment = (
        db.query(models.Enrollment)
        .options(joinedload(models.Enrollment.course))
        .filter(models.Enrollment.id == enrollment_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollment


# ==========================================
# PROGRESS TRACKING
# ==========================================

def _recompute_progress(db: Session, enrollment: models.Enrollment):
    total_lessons = db.query(models.Lesson).filter(models.Lesson.course_id == enrollment.course_id).count()
    if total_lessons == 0:
        enrollment.progress_percentage = 100.0
        return

    completed_lessons = (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.enrollment_id == enrollment.id,
            models.LessonProgress.completed == True,
        )
        .count()
    )
    pct = round((completed_lessons / total_lessons) * 100.0, 1)
    enrollment.progress_percentage = min(pct, 100.0)

    if enrollment.progress_percentage >= 100.0:
        enrollment.status = "completed"
        if not enrollment.completed_at:
            enrollment.completed_at = utcnow()
    else:
        if enrollment.status == "completed":
            enrollment.status = "active"

    db.commit()
    db.refresh(enrollment)


@router.post("/progress", response_model=schemas.ProgressOut, status_code=201)
def mark_progress(
    progress_in: schemas.ProgressMark,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == progress_in.enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    existing = (
        db.query(models.LessonProgress)
        .filter(
            models.LessonProgress.enrollment_id == progress_in.enrollment_id,
            models.LessonProgress.lesson_id == progress_in.lesson_id,
        )
        .first()
    )
    if existing:
        existing.completed = progress_in.completed
        existing.completed_at = utcnow() if progress_in.completed else None
        db.commit()
        db.refresh(existing)
        _recompute_progress(db, enrollment)
        return existing

    new_progress = models.LessonProgress(
        enrollment_id=progress_in.enrollment_id,
        lesson_id=progress_in.lesson_id,
        completed=progress_in.completed,
        completed_at=utcnow() if progress_in.completed else None,
    )
    db.add(new_progress)
    db.commit()
    db.refresh(new_progress)
    _recompute_progress(db, enrollment)
    return new_progress


@router.get("/{enrollment_id}/progress", response_model=list[schemas.ProgressOut])
def get_progress(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return (
        db.query(models.LessonProgress)
        .filter(models.LessonProgress.enrollment_id == enrollment_id)
        .all()
    )
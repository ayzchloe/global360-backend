from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/instructor", tags=["instructor"])


@router.get("/courses", response_model=list[schemas.CourseOut])
def get_instructor_courses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    """
    Required for /portal/instructor page.
    Returns courses taught by this instructor (or all if admin).
    """
    if current_user.role == "admin":
        return db.query(models.Course).all()

    courses = db.query(models.Course).filter(models.Course.instructor_id == current_user.id).all()
    # Fallback: if no courses specifically assigned yet, return all courses for convenience
    if not courses:
        return db.query(models.Course).all()
    return courses


@router.get("/stats")
def get_instructor_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    """
    Returns metrics for instructor dashboard cards.
    """
    total_courses = db.query(models.Course).count()
    pending_grading = (
        db.query(models.AssignmentSubmission)
        .filter(models.AssignmentSubmission.status == "submitted")
        .count()
    )
    total_students = db.query(models.Student).filter(models.Student.status == "active").count()
    upcoming_sessions = (
        db.query(models.LiveSession)
        .filter(models.LiveSession.status == "scheduled")
        .count()
    )

    return {
        "total_courses": total_courses,
        "pending_grading": pending_grading,
        "active_students": total_students,
        "upcoming_sessions": upcoming_sessions,
    }


@router.post("/courses/{course_id}/assign")
def assign_course_instructor(
    course_id: int,
    instructor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    instructor = db.query(models.User).filter(models.User.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor user not found")

    course.instructor_id = instructor_id
    db.commit()
    return {"message": f"Instructor '{instructor.name}' assigned to course '{course.title}'"}

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db, utcnow
import models
import schemas
import auth

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("/pending", response_model=list[schemas.PendingSubmissionOut])
def get_pending_assignments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    """
    Grading Queue required for /portal/instructor page.
    Returns all submissions with status 'submitted' awaiting grading.
    """
    submissions = (
        db.query(models.AssignmentSubmission)
        .filter(models.AssignmentSubmission.status == "submitted")
        .order_by(models.AssignmentSubmission.submitted_at.asc())
        .all()
    )

    results = []
    for sub in submissions:
        student_name = sub.student.user.name if sub.student and sub.student.user else f"Student #{sub.student_id}"
        course_id = sub.assignment.course.id if sub.assignment and sub.assignment.course else 0
        course_title = sub.assignment.course.title if sub.assignment and sub.assignment.course else "Unknown Course"
        results.append({
            "id": sub.id,
            "assignment_id": sub.assignment_id,
            "assignment_title": sub.assignment.title if sub.assignment else "Assignment",
            "course_id": course_id,
            "course_title": course_title,
            "student_id": sub.student_id,
            "student_name": student_name,
            "submitted_at": sub.submitted_at,
            "content": sub.content,
            "file_url": sub.file_url,
            "status": sub.status,
        })
    return results


@router.get("/course/{course_id}", response_model=list[schemas.AssignmentOut])
def get_course_assignments(course_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Assignment)
        .filter(models.Assignment.course_id == course_id)
        .all()
    )


@router.post("/", response_model=schemas.AssignmentOut, status_code=201)
def create_assignment(
    assignment_in: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    new_assignment = models.Assignment(**assignment_in.dict())
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return new_assignment


@router.get("/{assignment_id}", response_model=schemas.AssignmentOut)
def get_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.post("/{assignment_id}/submit", response_model=schemas.SubmissionOut, status_code=201)
def submit_assignment(
    assignment_id: int,
    submission_in: schemas.SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student profile required to submit assignments")

    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Check if existing submission
    existing = (
        db.query(models.AssignmentSubmission)
        .filter(
            models.AssignmentSubmission.assignment_id == assignment_id,
            models.AssignmentSubmission.student_id == student.id,
        )
        .first()
    )
    if existing:
        existing.content = submission_in.content
        existing.file_url = submission_in.file_url
        existing.submitted_at = utcnow()
        existing.status = "submitted"
        db.commit()
        db.refresh(existing)
        return existing

    new_submission = models.AssignmentSubmission(
        assignment_id=assignment_id,
        student_id=student.id,
        content=submission_in.content,
        file_url=submission_in.file_url,
        status="submitted",
        submitted_at=utcnow(),
    )
    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)
    return new_submission


@router.post("/submissions/{submission_id}/grade", response_model=schemas.SubmissionOut)
def grade_submission(
    submission_id: int,
    grade_in: schemas.GradeSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    submission = (
        db.query(models.AssignmentSubmission)
        .filter(models.AssignmentSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.grade = grade_in.grade
    submission.feedback = grade_in.feedback
    submission.status = "graded"
    submission.graded_at = utcnow()

    # Automatically notify student
    if submission.student and submission.student.user_id:
        notif = models.Notification(
            user_id=submission.student.user_id,
            title="Assignment Graded",
            message=f"Your submission for '{submission.assignment.title}' was graded: {grade_in.grade}/100",
            link="/portal/dashboard",
        )
        db.add(notif)

    db.commit()
    db.refresh(submission)
    return submission


@router.get("/student/{student_id}", response_model=list[schemas.SubmissionOut])
def get_student_submissions(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return (
        db.query(models.AssignmentSubmission)
        .filter(models.AssignmentSubmission.student_id == student_id)
        .all()
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/students", tags=["students"])


@router.post("/", response_model=schemas.StudentOut, status_code=201)
def create_student(
    student_in: schemas.StudentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = db.query(models.Student).filter(models.Student.user_id == student_in.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student profile already exists for this user")

    new_student = models.Student(
        user_id=student_in.user_id,
        program=student_in.program,
        status=student_in.status or "active",
        enrollment_no=student_in.enrollment_no or f"G360-{student_in.user_id:04d}",
        github_url=student_in.github_url,
        linkedin_url=student_in.linkedin_url,
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student


@router.get("/me", response_model=schemas.StudentOut)
def get_my_student_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    student = db.query(models.Student).filter(models.Student.user_id == current_user.id).first()
    if not student:
        # Auto-create profile if missing
        student = models.Student(
            user_id=current_user.id,
            enrollment_no=f"G360-{current_user.id:04d}",
            program="General Studies",
            status="active",
        )
        db.add(student)
        db.commit()
        db.refresh(student)
    return student


@router.get("/", response_model=list[schemas.StudentOut])
def list_students(
    program: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.Student)
    if program:
        query = query.filter(models.Student.program == program)
    if status_filter:
        query = query.filter(models.Student.status == status_filter)
    return query.all()


@router.get("/{student_id}", response_model=schemas.StudentOut)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/{student_id}", response_model=schemas.StudentOut)
def update_student(
    student_id: int,
    student_in: schemas.StudentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Only admin or the student themselves can update
    if current_user.role != "admin" and student.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this student profile")

    if student_in.program is not None:
        student.program = student_in.program
    if student_in.status is not None:
        student.status = student_in.status
    if student_in.enrollment_no is not None:
        student.enrollment_no = student_in.enrollment_no
    if student_in.github_url is not None:
        student.github_url = student_in.github_url
    if student_in.linkedin_url is not None:
        student.linkedin_url = student_in.linkedin_url

    db.commit()
    db.refresh(student)
    return student
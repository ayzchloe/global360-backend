from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/", response_model=list[schemas.CourseOut])
def list_courses(
    track: str | None = None,
    level: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Public course catalog backing the /programs and home pages.
    """
    query = db.query(models.Course).filter(models.Course.is_published == True)
    if track:
        query = query.filter(models.Course.track == track)
    if level:
        query = query.filter(models.Course.level == level)
    return query.order_by(models.Course.order).all()


@router.get("/{course_id}", response_model=schemas.CourseDetailOut)
def get_course(course_id: int, db: Session = Depends(get_db)):
    """
    Public course detail with full syllabus (modules and lessons).
    """
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post("/", response_model=schemas.CourseOut, status_code=201)
def create_course(
    course_in: schemas.CourseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """
    Admin-only: add a new course to the curriculum.
    """
    new_course = models.Course(**course_in.dict())
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@router.put("/{course_id}", response_model=schemas.CourseOut)
def update_course(
    course_id: int,
    course_in: schemas.CourseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    for field, value in course_in.dict(exclude_unset=True).items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=200)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return {"message": f"Course '{course.title}' deleted successfully"}


@router.post("/{course_id}/modules", response_model=schemas.ModuleOut, status_code=201)
def add_module(
    course_id: int,
    module_in: schemas.ModuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    new_module = models.Module(course_id=course_id, **module_in.dict())
    db.add(new_module)
    db.commit()
    db.refresh(new_module)
    return new_module


@router.post("/{course_id}/lessons", response_model=schemas.LessonOut, status_code=201)
def add_lesson(
    course_id: int,
    lesson_in: schemas.LessonCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    new_lesson = models.Lesson(course_id=course_id, **lesson_in.dict())
    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)
    return new_lesson


@router.put("/lessons/{lesson_id}", response_model=schemas.LessonOut)
def update_lesson(
    lesson_id: int,
    lesson_in: schemas.LessonUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    for field, value in lesson_in.dict(exclude_unset=True).items():
        setattr(lesson, field, value)

    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/lessons/{lesson_id}", status_code=200)
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    db.delete(lesson)
    db.commit()
    return {"message": "Lesson deleted successfully"}
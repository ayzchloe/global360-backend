from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db, utcnow
import models
import schemas
import auth

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/", response_model=list[schemas.SessionOut])
def list_sessions(
    course_id: int | None = None,
    upcoming_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Backs upcoming sessions on /portal/dashboard and /portal/instructor.
    """
    query = db.query(models.LiveSession)
    if course_id:
        query = query.filter(models.LiveSession.course_id == course_id)
    if upcoming_only:
        query = query.filter(models.LiveSession.scheduled_time >= utcnow())
    return query.order_by(models.LiveSession.scheduled_time.asc()).all()


@router.post("/", response_model=schemas.SessionOut, status_code=201)
def schedule_session(
    session_in: schemas.SessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    """
    Required for 'Schedule Session' action on /portal/instructor.
    """
    instructor_name = session_in.instructor_name or current_user.name
    new_session = models.LiveSession(
        title=session_in.title,
        course_id=session_in.course_id,
        instructor_id=current_user.id,
        instructor_name=instructor_name,
        scheduled_time=session_in.scheduled_time,
        duration_minutes=session_in.duration_minutes,
        meeting_link=session_in.meeting_link,
        session_type=session_in.session_type or "Live Lecture",
        status="scheduled",
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Broadcast notification to enrolled students if course_id is set
    if session_in.course_id:
        enrollments = (
            db.query(models.Enrollment)
            .filter(models.Enrollment.course_id == session_in.course_id)
            .all()
        )
        for enr in enrollments:
            if enr.student and enr.student.user_id:
                notif = models.Notification(
                    user_id=enr.student.user_id,
                    title=f"New Class Scheduled: {new_session.title}",
                    message=f"Scheduled for {new_session.scheduled_time.strftime('%Y-%m-%d %H:%M')}. Join link ready.",
                    link=new_session.meeting_link,
                )
                db.add(notif)
        db.commit()

    return new_session


@router.get("/{session_id}", response_model=schemas.SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session_obj = db.query(models.LiveSession).filter(models.LiveSession.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_obj


@router.put("/{session_id}", response_model=schemas.SessionOut)
def update_session(
    session_id: int,
    session_in: schemas.SessionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    session_obj = db.query(models.LiveSession).filter(models.LiveSession.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    for field, val in session_in.dict(exclude_unset=True).items():
        setattr(session_obj, field, val)

    db.commit()
    db.refresh(session_obj)
    return session_obj


@router.delete("/{session_id}", status_code=200)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    session_obj = db.query(models.LiveSession).filter(models.LiveSession.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session_obj)
    db.commit()
    return {"message": "Session deleted successfully"}

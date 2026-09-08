from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=list[schemas.NotificationOut])
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Required for /portal/dashboard notifications bell / feed.
    """
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == current_user.id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )


@router.get("/student/{student_id}", response_model=list[schemas.NotificationOut])
def get_student_notifications(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == student.user_id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )


@router.post("/", response_model=schemas.NotificationOut, status_code=201)
def create_notification(
    notif_in: schemas.NotificationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    new_notif = models.Notification(**notif_in.dict())
    db.add(new_notif)
    db.commit()
    db.refresh(new_notif)
    return new_notif


@router.put("/{notification_id}/read", response_model=schemas.NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notif.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/read-all", status_code=200)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}

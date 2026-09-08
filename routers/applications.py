from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/applications", tags=["applications"])


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


# ADMIN-ONLY — update status of admissions application (accept/reject)
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
    db.commit()
    db.refresh(app_record)
    return app_record


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
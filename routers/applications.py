from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/applications", tags=["applications"])


# PUBLIC — matches the "Apply Now" button on every page, no login needed
@router.post("/", response_model=schemas.ApplicationOut, status_code=201)
def submit_application(app_in: schemas.ApplicationCreate, db: Session = Depends(get_db)):
    new_app = models.Application(**app_in.dict())
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    return new_app


# ADMIN-ONLY — view submitted applications
@router.get("/", response_model=list[schemas.ApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Application).all()


# PUBLIC — matches the newsletter box on the Blog page
@router.post("/newsletter", status_code=201)
def subscribe_newsletter(sub: schemas.NewsletterCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.NewsletterSubscriber)
        .filter(models.NewsletterSubscriber.email == sub.email)
        .first()
    )
    if existing:
        return {"message": "Already subscribed"}

    new_sub = models.NewsletterSubscriber(email=sub.email)
    db.add(new_sub)
    db.commit()
    return {"message": "Subscribed successfully"}
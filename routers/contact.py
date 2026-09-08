from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(tags=["contact"])


@router.post("/contact/", response_model=schemas.ContactInquiryOut, status_code=201)
@router.post("/inquiries/", response_model=schemas.ContactInquiryOut, status_code=201)
def submit_contact_inquiry(
    inquiry_in: schemas.ContactInquiryCreate,
    db: Session = Depends(get_db),
):
    """
    Public — backs the /contact form.
    """
    new_inquiry = models.ContactInquiry(**inquiry_in.dict())
    db.add(new_inquiry)
    db.commit()
    db.refresh(new_inquiry)
    return new_inquiry


@router.get("/contact/", response_model=list[schemas.ContactInquiryOut])
@router.get("/inquiries/", response_model=list[schemas.ContactInquiryOut])
def list_inquiries(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """
    Admin-only: list student & prospect inquiries.
    """
    query = db.query(models.ContactInquiry)
    if status_filter:
        query = query.filter(models.ContactInquiry.status == status_filter)
    return query.order_by(models.ContactInquiry.created_at.desc()).all()


@router.patch("/contact/{inquiry_id}/status", response_model=schemas.ContactInquiryOut)
def update_inquiry_status(
    inquiry_id: int,
    status_in: schemas.InquiryStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    inquiry = db.query(models.ContactInquiry).filter(models.ContactInquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    inquiry.status = status_in.status
    db.commit()
    db.refresh(inquiry)
    return inquiry

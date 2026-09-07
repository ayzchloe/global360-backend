from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post("/", response_model=schemas.CertificateOut, status_code=201)
def issue_certificate(
    cert_in: schemas.CertificateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    existing = (
        db.query(models.Certificate)
        .filter(models.Certificate.certificate_id == cert_in.certificate_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Certificate ID already exists")

    new_cert = models.Certificate(**cert_in.dict())
    db.add(new_cert)
    db.commit()
    db.refresh(new_cert)
    return new_cert


@router.get("/student/{student_id}", response_model=list[schemas.CertificateOut])
def get_student_certificates(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return (
        db.query(models.Certificate)
        .filter(models.Certificate.student_id == student_id)
        .all()
    )


# PUBLIC route — matches the frontend's /verify page, no auth required
@router.get("/verify/{certificate_id}")
def verify_certificate(certificate_id: str, db: Session = Depends(get_db)):
    cert = (
        db.query(models.Certificate)
        .filter(models.Certificate.certificate_id == certificate_id)
        .first()
    )
    if not cert or cert.status != "valid":
        return {"valid": False, "message": "Certificate not found or invalid"}

    return {
        "valid": True,
        "certificate_id": cert.certificate_id,
        "course_name": cert.course_name,
        "issued_date": cert.issued_date,
        "student_name": cert.student.user.name,
    }
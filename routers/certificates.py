import io
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth
from pdf_generator import generate_certificate_pdf

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post("/", response_model=schemas.CertificateOut, status_code=201)
def issue_certificate(
    cert_in: schemas.CertificateCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_instructor_or_admin),
):
    student = db.query(models.Student).filter(models.Student.id == cert_in.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    existing = (
        db.query(models.Certificate)
        .filter(models.Certificate.certificate_id == cert_in.certificate_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Certificate ID already exists")

    new_cert = models.Certificate(
        student_id=cert_in.student_id,
        certificate_id=cert_in.certificate_id,
        course_name=cert_in.course_name,
        issued_date=cert_in.issued_date,
        grade=cert_in.grade or "Distinction",
        status=cert_in.status or "valid",
        skills=cert_in.skills,
        verification_code=auth.secrets.token_hex(6).upper(),
    )
    db.add(new_cert)

    # Notify student
    if student.user_id:
        notif = models.Notification(
            user_id=student.user_id,
            title="Certificate Issued!",
            message=f"Congratulations! Your certificate for {cert_in.course_name} has been issued.",
            link=f"/verify/{cert_in.certificate_id}",
        )
        db.add(notif)

    db.commit()
    db.refresh(new_cert)
    return new_cert


@router.get("/student/{student_id}", response_model=list[schemas.CertificateOut])
def get_student_certificates(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Backs certificates card on /portal/dashboard.
    """
    return (
        db.query(models.Certificate)
        .filter(models.Certificate.student_id == student_id)
        .all()
    )


@router.get("/verify/{certificate_id}", response_model=schemas.CertificateVerifyOut)
def verify_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    PUBLIC route — backs the frontend's /verify/[id] page.
    Returns complete verification data structure.
    """
    cert = (
        db.query(models.Certificate)
        .filter(models.Certificate.certificate_id == certificate_id)
        .first()
    )
    if not cert:
        return schemas.CertificateVerifyOut(
            valid=False,
            certificate_id=certificate_id,
            message="Certificate ID not found in Global360 verification registry.",
        )

    if cert.status != "valid":
        return schemas.CertificateVerifyOut(
            valid=False,
            certificate_id=cert.certificate_id,
            status=cert.status,
            message=f"This certificate is flagged as {cert.status}.",
        )

    student_name = cert.student.user.name if cert.student and cert.student.user else "Global360 Graduate"
    skills_list = [s.strip() for s in cert.skills.split(",")] if cert.skills else [
        "Core Concepts",
        "Practical Implementation",
        "Industry Best Practices",
    ]

    return schemas.CertificateVerifyOut(
        valid=True,
        certificate_id=cert.certificate_id,
        course_name=cert.course_name,
        student_name=student_name,
        issued_date=cert.issued_date,
        grade=cert.grade or "Distinction",
        skills=skills_list,
        status="valid",
        credential_url=f"/verify/{cert.certificate_id}",
        pdf_url=f"/certificates/{cert.certificate_id}/pdf",
        message="Official credential verified by Global360 Registry.",
    )


# ==========================================
# CERTIFICATE PDF GENERATION & DOWNLOAD
# ==========================================

def _stream_certificate_pdf(cert: models.Certificate):
    student_name = cert.student.user.name if cert.student and cert.student.user else "Global360 Graduate"
    pdf_bytes = generate_certificate_pdf(
        student_name=student_name,
        course_name=cert.course_name,
        certificate_id=cert.certificate_id,
        issued_date=cert.issued_date,
        grade=cert.grade or "Distinction",
        skills=cert.skills,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="Global360_Certificate_{cert.certificate_id}.pdf"'
        },
    )


@router.get("/{certificate_id}/pdf")
def download_certificate_pdf(certificate_id: str, db: Session = Depends(get_db)):
    """
    Required for 'Download PDF' on /verify page.
    Dynamically renders high-resolution Global360 certificate PDF.
    """
    cert = (
        db.query(models.Certificate)
        .filter(models.Certificate.certificate_id == certificate_id)
        .first()
    )
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    return _stream_certificate_pdf(cert)


@router.get("/verify/{certificate_id}/pdf")
def download_verified_certificate_pdf(certificate_id: str, db: Session = Depends(get_db)):
    """
    Direct alias matching verify page download action.
    """
    return download_certificate_pdf(certificate_id=certificate_id, db=db)
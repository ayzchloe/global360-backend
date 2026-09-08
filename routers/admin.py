from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models
import schemas
import auth

router = APIRouter(tags=["admin"])


# ==========================================
# AUDIT LOG ENDPOINTS (Backs /portal/admin)
# ==========================================

@router.get("/audit-log/", response_model=list[schemas.AuditLogOut])
@router.get("/audit-logs/", response_model=list[schemas.AuditLogOut])
def get_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """
    Required for /portal/admin Audit Log section.
    """
    return (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )


# ==========================================
# ADMIN DASHBOARD STATS
# ==========================================

@router.get("/admin/stats", response_model=schemas.AdminStatsOut)
def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """
    Required for /portal/admin overview metric cards.
    """
    total_students = db.query(models.Student).count()
    active_enrollments = db.query(models.Enrollment).filter(models.Enrollment.status == "active").count()
    total_courses = db.query(models.Course).count()
    pending_applications = db.query(models.Application).filter(models.Application.status == "pending").count()
    pending_assignments = db.query(models.AssignmentSubmission).filter(models.AssignmentSubmission.status == "submitted").count()
    total_certificates = db.query(models.Certificate).count()
    
    # Revenue calculations from fee challans
    paid_challans = db.query(models.FeeChallan).filter(models.FeeChallan.status == "paid").all()
    total_revenue = sum(c.amount for c in paid_challans)
    total_challans = db.query(models.FeeChallan).count()

    return schemas.AdminStatsOut(
        total_students=total_students,
        active_enrollments=active_enrollments,
        total_courses=total_courses,
        pending_applications=pending_applications,
        pending_assignments=pending_assignments,
        total_certificates_issued=total_certificates,
        total_revenue=total_revenue,
        total_challans_issued=total_challans,
        paid_challans=len(paid_challans),
    )


# ==========================================
# USER MANAGEMENT
# ==========================================

@router.get("/admin/users", response_model=list[schemas.UserOut])
def list_users(
    role: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    return query.order_by(models.User.created_at.desc()).all()


@router.put("/admin/users/{user_id}/role", response_model=schemas.UserOut)
def change_user_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    if role not in ("student", "instructor", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    db.commit()
    db.refresh(user)
    return user

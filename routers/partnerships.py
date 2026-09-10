from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/partnerships", tags=["partnerships"])


@router.get("/", response_model=list[schemas.PartnershipOut])
def list_partnerships(
    partnership_type: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Public — backs the /partnerships page.
    """
    query = db.query(models.Partnership).filter(models.Partnership.status == "active")
    if partnership_type:
        query = query.filter(models.Partnership.partnership_type == partnership_type)
    return query.order_by(models.Partnership.created_at.desc()).all()


@router.post("/", response_model=schemas.PartnershipOut, status_code=201)
def add_partnership(
    partner_in: schemas.PartnershipCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """
    Required for 'Add Partnership' on /portal/admin page.
    """
    new_partner = models.Partnership(**partner_in.dict())
    db.add(new_partner)
    db.commit()
    db.refresh(new_partner)
    return new_partner


@router.delete("/{partnership_id}", status_code=200)
def delete_partnership(
    partnership_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    partner = db.query(models.Partnership).filter(models.Partnership.id == partnership_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partnership not found")
    db.delete(partner)
    db.commit()
    return {"message": "Partnership deleted successfully"}


from schemas import PartnershipUpdate


@router.patch("/{partnership_id}", response_model=schemas.PartnershipOut)
def update_partnership(
    partnership_id: int,
    update_in: PartnershipUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """Allows changing partnership status (e.g. active -> archived) and other fields."""
    partner = db.query(models.Partnership).filter(models.Partnership.id == partnership_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partnership not found")
    update_data = update_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(partner, field, value)
    db.commit()
    db.refresh(partner)
    return partner

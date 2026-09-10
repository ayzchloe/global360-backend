from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth

router = APIRouter(tags=["finance"])


# ==========================================
# FEE CHALLANS
# ==========================================

@router.post("/fee-challans/", response_model=schemas.FeeChallanOut, status_code=201)
def issue_challan(
    challan_in: schemas.FeeChallanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """
    Required for 'Issue Challan' on /portal/admin page.
    """
    student = db.query(models.Student).filter(models.Student.id == challan_in.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    challan_count = db.query(models.FeeChallan).count() + 1
    challan_no = f"CHAL-{date.today().strftime('%Y%m')}-{challan_count:04d}"

    new_challan = models.FeeChallan(
        challan_no=challan_no,
        student_id=challan_in.student_id,
        title=challan_in.title or "Semester Tuition Fee",
        program=challan_in.program or student.program or "General Studies",
        amount=challan_in.amount,
        due_date=challan_in.due_date,
        status=challan_in.status or "pending",
        issued_date=date.today(),
    )
    db.add(new_challan)

    # Notify student
    if student.user_id:
        notif = models.Notification(
            user_id=student.user_id,
            title="Fee Challan Issued",
            message=f"A new fee voucher of ${challan_in.amount:.2f} has been issued. Due: {challan_in.due_date}",
            link="/portal/dashboard",
        )
        db.add(notif)

    db.commit()
    db.refresh(new_challan)
    return new_challan


@router.get("/fee-challans/", response_model=list[schemas.FeeChallanOut])
def list_challans(
    student_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    query = db.query(models.FeeChallan)
    if student_id:
        query = query.filter(models.FeeChallan.student_id == student_id)
    if status_filter:
        query = query.filter(models.FeeChallan.status == status_filter)
    return query.order_by(models.FeeChallan.issued_date.desc()).all()


@router.get("/fee-challans/student/{student_id}", response_model=list[schemas.FeeChallanOut])
def get_student_challans(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return (
        db.query(models.FeeChallan)
        .filter(models.FeeChallan.student_id == student_id)
        .order_by(models.FeeChallan.issued_date.desc())
        .all()
    )


@router.get("/fee-challans/{challan_id}", response_model=schemas.FeeChallanOut)
def get_challan(challan_id: int, db: Session = Depends(get_db)):
    challan = db.query(models.FeeChallan).filter(models.FeeChallan.id == challan_id).first()
    if not challan:
        raise HTTPException(status_code=404, detail="Fee Challan not found")
    return challan


@router.put("/fee-challans/{challan_id}/pay", response_model=schemas.FeeChallanOut)
def pay_challan(
    challan_id: int,
    pay_in: schemas.FeeChallanPayRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    challan = db.query(models.FeeChallan).filter(models.FeeChallan.id == challan_id).first()
    if not challan:
        raise HTTPException(status_code=404, detail="Fee Challan not found")

    challan.status = "paid"
    challan.payment_method = pay_in.payment_method
    challan.paid_date = date.today()

    db.commit()
    db.refresh(challan)
    return challan


# ==========================================
# PAYMENT ACCOUNTS
# ==========================================

@router.post("/payment-accounts/", response_model=schemas.PaymentAccountOut, status_code=201)
def add_payment_account(
    account_in: schemas.PaymentAccountCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """
    Required for 'Add Payment Account' on /portal/admin page.
    """
    new_account = models.PaymentAccount(**account_in.dict())
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account


@router.get("/payment-accounts/", response_model=list[schemas.PaymentAccountOut])
def list_payment_accounts(db: Session = Depends(get_db)):
    """
    Publicly list active banking/payment accounts so students know where to pay.
    """
    return db.query(models.PaymentAccount).filter(models.PaymentAccount.is_active == True).all()


@router.delete("/payment-accounts/{account_id}", status_code=200)
def delete_payment_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    account = db.query(models.PaymentAccount).filter(models.PaymentAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Payment account not found")
    db.delete(account)
    db.commit()
    return {"message": "Payment account deleted successfully"}


from fastapi.responses import Response
from pdf_generator import generate_fee_challan_pdf


@router.patch("/payment-accounts/{account_id}/default", response_model=schemas.PaymentAccountOut)
def set_default_payment_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
):
    """Marks the given account as default and unsets is_default on all others."""
    account = db.query(models.PaymentAccount).filter(models.PaymentAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Payment account not found")
    db.query(models.PaymentAccount).filter(models.PaymentAccount.id != account_id).update({"is_default": False})
    account.is_default = True
    db.commit()
    db.refresh(account)
    return account


@router.get("/fee-challans/{challan_id}/pdf")
def download_fee_challan_pdf(challan_id: int, db: Session = Depends(get_db)):
    """Dynamically renders a printable Fee Challan / Payment Voucher PDF."""
    challan = db.query(models.FeeChallan).filter(models.FeeChallan.id == challan_id).first()
    if not challan:
        raise HTTPException(status_code=404, detail="Fee Challan not found")
    student_name = challan.student.user.name if challan.student and challan.student.user else "Global360 Student"
    default_account = (
        db.query(models.PaymentAccount)
        .filter(models.PaymentAccount.is_default == True, models.PaymentAccount.is_active == True)
        .first()
    )
    account_number = default_account.account_number if default_account else None
    instructions = default_account.instructions if default_account else None
    pdf_bytes = generate_fee_challan_pdf(
        challan_no=challan.challan_no,
        student_name=student_name,
        program=challan.program or "General Studies",
        title=challan.title,
        amount=challan.amount,
        due_date=challan.due_date,
        issued_date=challan.issued_date,
        status=challan.status,
        payment_method=challan.payment_method,
        account_number=account_number,
        instructions=instructions,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="Global360_Fee_Challan_{}.pdf"'.format(challan.challan_no)},
    )

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt

from app.core.db import SessionLocal
from app.models.account import Account
from app.models.payment import Payment

router = APIRouter(prefix="/payment", tags=["payment"])

SECRET_KEY = "SECRET123"
ALGORITHM = "HS256"
ADMIN_PAYMENT_KEY = "PAYMENT_ADMIN_123"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_account(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        account_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return account


def require_admin_key(admin_key: str):
    if admin_key != ADMIN_PAYMENT_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


def get_plan_amount(plan_name: str):
    if plan_name == "basic":
        return 10000, 30, 100

    if plan_name == "pro":
        return 30000, 30, 1000

    if plan_name == "enterprise":
        return 100000, 30, 1000000

    raise HTTPException(status_code=400, detail="Invalid plan")


def get_provider_payload(provider: str, plan_name: str, amount: int):
    if provider == "manual":
        return {
            "payment_url": None,
            "comment": f"Ручная оплата тарифа {plan_name} на сумму {amount} KZT"
        }

    if provider == "kaspi":
        return {
            "payment_url": None,
            "comment": f"Kaspi оплата тарифа {plan_name} на сумму {amount} KZT"
        }

    if provider == "stripe":
        return {
            "payment_url": None,
            "comment": f"Stripe оплата тарифа {plan_name} на сумму {amount} KZT"
        }

    raise HTTPException(status_code=400, detail="Invalid provider")


@router.post("/create")
def create_payment(
    token: str,
    plan_name: str = "basic",
    provider: str = "manual",
    db: Session = Depends(get_db)
):
    try:
        account = get_current_account(token, db)

        amount, period_days, _ = get_plan_amount(plan_name)
        provider_payload = get_provider_payload(provider, plan_name, amount)

        payment = Payment(
            account_id=account.id,
            amount=amount,
            currency="KZT",
            status="pending",
            provider=provider,
            plan_name=plan_name,
            period_days=period_days,
            payment_url=provider_payload["payment_url"],
            comment=provider_payload["comment"]
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        return {
            "status": "payment_created",
            "payment_id": payment.id,
            "plan_name": payment.plan_name,
            "amount": payment.amount,
            "currency": payment.currency,
            "provider": payment.provider,
            "payment_url": payment.payment_url,
            "comment": payment.comment
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
def list_payments(token: str, db: Session = Depends(get_db)):
    try:
        account = get_current_account(token, db)

        payments = (
            db.query(Payment)
            .filter(Payment.account_id == account.id)
            .order_by(Payment.created_at.desc())
            .all()
        )

        return [
            {
                "id": payment.id,
                "amount": payment.amount,
                "currency": payment.currency,
                "status": payment.status,
                "provider": payment.provider,
                "plan_name": payment.plan_name,
                "period_days": payment.period_days,
                "external_payment_id": payment.external_payment_id,
                "payment_url": payment.payment_url,
                "comment": payment.comment,
                "created_at": payment.created_at,
                "paid_at": payment.paid_at,
            }
            for payment in payments
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def payment_status(
    token: str,
    payment_id: int,
    db: Session = Depends(get_db)
):
    try:
        account = get_current_account(token, db)

        payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment_id,
                Payment.account_id == account.id
            )
            .first()
        )

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        return {
            "id": payment.id,
            "status": payment.status,
            "provider": payment.provider,
            "plan_name": payment.plan_name,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_url": payment.payment_url,
            "comment": payment.comment,
            "created_at": payment.created_at,
            "paid_at": payment.paid_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm")
def confirm_payment(
    payment_id: int,
    admin_key: str,
    db: Session = Depends(get_db)
):
    try:
        require_admin_key(admin_key)

        payment = db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.status == "paid":
            return {
                "status": "already_paid",
                "payment_id": payment.id
            }

        account = db.query(Account).filter(Account.id == payment.account_id).first()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        _, period_days, messages_limit = get_plan_amount(payment.plan_name)

        now = datetime.utcnow()

        if account.paid_until and account.paid_until > now:
            account.paid_until = account.paid_until + timedelta(days=period_days)
        else:
            account.paid_until = now + timedelta(days=period_days)

        account.subscription_active = True
        account.billing_status = "paid"
        account.plan_name = payment.plan_name
        account.messages_used = 0
        account.messages_limit = messages_limit
        account.updated_at = datetime.utcnow()

        payment.status = "paid"
        payment.paid_at = datetime.utcnow()

        db.commit()
        db.refresh(account)
        db.refresh(payment)

        return {
            "status": "payment_confirmed",
            "payment_id": payment.id,
            "account_id": account.id,
            "plan_name": account.plan_name,
            "subscription_active": account.subscription_active,
            "billing_status": account.billing_status,
            "paid_until": account.paid_until,
            "messages_used": account.messages_used,
            "messages_limit": account.messages_limit
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject")
def reject_payment(
    payment_id: int,
    admin_key: str,
    comment: str = "",
    db: Session = Depends(get_db)
):
    try:
        require_admin_key(admin_key)

        payment = db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.status == "paid":
            raise HTTPException(status_code=400, detail="Paid payment cannot be rejected")

        payment.status = "rejected"
        payment.comment = comment or payment.comment

        db.commit()
        db.refresh(payment)

        return {
            "status": "payment_rejected",
            "payment_id": payment.id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import requests

from app.core.db import SessionLocal
from app.models.account import Account
from jose import jwt

router = APIRouter(prefix="/account", tags=["account"])

SECRET_KEY = "SECRET123"
ALGORITHM = "HS256"


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


def refresh_subscription(account: Account):
    now = datetime.utcnow()

    if account.paid_until and account.paid_until > now:
        account.subscription_active = True
        if account.billing_status != "paid":
            account.billing_status = "paid"
    else:
        account.subscription_active = False
        if account.billing_status == "paid":
            account.billing_status = "pending_payment"


def apply_plan(account: Account, plan_name: str):
    if plan_name == "basic":
        account.plan_name = "basic"
        account.messages_limit = 100
        return

    if plan_name == "pro":
        account.plan_name = "pro"
        account.messages_limit = 1000
        return

    if plan_name == "enterprise":
        account.plan_name = "enterprise"
        account.messages_limit = 1000000
        return

    raise HTTPException(status_code=400, detail="Invalid plan")


@router.get("/me")
def account_me(token: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    refresh_subscription(account)
    db.commit()
    db.refresh(account)

    return {
        "id": account.id,
        "email": account.email,
        "company_name": account.company_name,
        "phone": account.phone,
        "is_paused": account.is_paused,
        "manager_connected": account.manager_connected,
        "plan_name": account.plan_name,
        "billing_status": account.billing_status,
        "subscription_active": account.subscription_active,
        "paid_until": account.paid_until,
        "messages_used": account.messages_used,
        "messages_limit": account.messages_limit,
        "green_id_instance": account.green_id_instance,
        "green_connected": account.green_connected,
        "green_status": account.green_status,
        "green_phone": account.green_phone,
        "onboarding_completed": account.onboarding_completed,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


@router.post("/green/connect")
def connect_green(
    token: str,
    id_instance: str,
    api_token: str,
    db: Session = Depends(get_db)
):
    account = get_current_account(token, db)

    existing_account = (
        db.query(Account)
        .filter(
            Account.green_id_instance == id_instance,
            Account.id != account.id
        )
        .first()
    )

    if existing_account:
        raise HTTPException(status_code=400, detail="This Green API instance is already connected to another account")

    account.green_id_instance = id_instance
    account.green_api_token = api_token
    account.green_connected = False
    account.green_status = "checking"
    account.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(account)

    return {
        "status": "saved",
        "green_id_instance": account.green_id_instance,
        "green_status": account.green_status
    }


@router.post("/green/disconnect")
def disconnect_green(token: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    account.green_id_instance = None
    account.green_api_token = None
    account.green_connected = False
    account.green_status = "not_connected"
    account.green_phone = None
    account.updated_at = datetime.utcnow()

    db.commit()

    return {"status": "disconnected"}


@router.get("/green/status")
def green_status(token: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    if not account.green_id_instance or not account.green_api_token:
        account.green_connected = False
        account.green_status = "not_connected"
        account.green_phone = None
        account.updated_at = datetime.utcnow()
        db.commit()

        return {
            "status": "not_connected",
            "connected": False,
            "phone": None
        }

    url = f"https://api.green-api.com/waInstance{account.green_id_instance}/getStateInstance/{account.green_api_token}"

    try:
        res = requests.get(url, timeout=20)
        data = res.json()

        state = data.get("stateInstance")

        if state == "authorized":
            account.green_connected = True
            account.green_status = "authorized"
        else:
            account.green_connected = False
            account.green_status = state or "unknown"

        account.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(account)

        return {
            "status": account.green_status,
            "connected": account.green_connected,
            "phone": account.green_phone
        }

    except Exception as e:
        account.green_connected = False
        account.green_status = "error"
        account.updated_at = datetime.utcnow()
        db.commit()

        return {
            "status": "error",
            "detail": str(e)
        }


@router.post("/bot/pause")
def pause_bot(token: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    account.is_paused = True
    account.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "bot_paused",
        "is_paused": account.is_paused
    }


@router.post("/bot/resume")
def resume_bot(token: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    account.is_paused = False
    account.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "bot_resumed",
        "is_paused": account.is_paused
    }


@router.post("/manager/connect")
def connect_manager(token: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    account.manager_connected = True
    account.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "manager_connected",
        "manager_connected": account.manager_connected
    }


@router.post("/manager/disconnect")
def disconnect_manager(token: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    account.manager_connected = False
    account.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "manager_disconnected",
        "manager_connected": account.manager_connected
    }


@router.post("/activate-subscription")
def activate_subscription(
    token: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    account = get_current_account(token, db)

    now = datetime.utcnow()

    if account.paid_until and account.paid_until > now:
        account.paid_until = account.paid_until + timedelta(days=days)
    else:
        account.paid_until = now + timedelta(days=days)

    account.subscription_active = True
    account.billing_status = "paid"
    account.messages_used = 0
    account.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(account)

    return {
        "status": "subscription_activated",
        "subscription_active": account.subscription_active,
        "billing_status": account.billing_status,
        "paid_until": account.paid_until,
        "messages_used": account.messages_used,
        "messages_limit": account.messages_limit
    }


@router.get("/subscription/status")
def subscription_status(token: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    refresh_subscription(account)
    account.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(account)

    return {
        "subscription_active": account.subscription_active,
        "billing_status": account.billing_status,
        "plan_name": account.plan_name,
        "paid_until": account.paid_until,
        "messages_used": account.messages_used,
        "messages_limit": account.messages_limit
    }


@router.post("/subscription/reset-limit")
def reset_limit(token: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    account.messages_used = 0
    account.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(account)

    return {
        "status": "limit_reset",
        "messages_used": account.messages_used,
        "messages_limit": account.messages_limit
    }


@router.post("/subscription/set-plan")
def set_plan(token: str, plan_name: str, db: Session = Depends(get_db)):
    account = get_current_account(token, db)

    apply_plan(account, plan_name)
    account.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(account)

    return {
        "status": "plan_updated",
        "plan_name": account.plan_name,
        "messages_limit": account.messages_limit
    }
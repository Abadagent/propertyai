from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

from app.core.db import SessionLocal
from app.models.account import Account

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = "SECRET123"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_token(account_id: int) -> str:
    payload = {
        "sub": str(account_id),
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_token_with_payload(account: Account) -> str:
    payload = {
        "sub": str(account.id),
        "email": account.email,
        "plan": account.plan_name,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register")
def register(email: str, password: str, db: Session = Depends(get_db)):
    existing = db.query(Account).filter(Account.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    account = Account(
        email=email,
        password_hash=hash_password(password),
        billing_status="pending_payment",
        subscription_active=False,
        green_connected=False,
        green_status="not_connected",
        plan_name="basic",
        is_paused=False,
        manager_connected=False,
        onboarding_completed=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(account)
    db.commit()
    db.refresh(account)

    token = create_token_with_payload(account)

    return {
        "token": token,
        "account_id": account.id,
        "email": account.email,
        "plan": account.plan_name
    }


@router.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.email == email).first()

    if not account:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(password, account.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    account.updated_at = datetime.utcnow()
    db.commit()

    token = create_token_with_payload(account)

    return {
        "token": token,
        "account_id": account.id,
        "email": account.email,
        "plan": account.plan_name
    }


@router.get("/me")
def auth_me(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        account_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return {
        "id": account.id,
        "email": account.email,
        "plan": account.plan_name,
        "subscription_active": account.subscription_active,
        "billing_status": account.billing_status
    }
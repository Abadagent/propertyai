from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import jwt

from app.core.db import SessionLocal
from app.schemas.chat import ChatMessageIn
from app.services.chat_logic import process_message
from app.models.account import Account

router = APIRouter(prefix="", tags=["default"])

SECRET_KEY = "SECRET123"
ALGORITHM = "HS256"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_account_by_token(token: str, db: Session) -> Account:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        account_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return account


@router.post("/chat")
def chat(message: ChatMessageIn, db: Session = Depends(get_db)):
    account = get_account_by_token(message.token, db)

    return process_message(
        db=db,
        account=account,
        phone=message.phone,
        text=message.text,
    )
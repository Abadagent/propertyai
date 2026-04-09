from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.conversation import Conversation

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/manager/connect")
def manager_connect(phone: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.phone == phone).first()

    if not conversation:
        return {"status": "not_found"}

    conversation.manager_connected = True
    db.commit()

    return {"status": "ok"}
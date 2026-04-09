from fastapi import FastAPI
import threading
from datetime import datetime

from app.models import *
from app.core.db import Base, engine, SessionLocal

from app.webhook_green import router as green_router

from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.account import router as account_router
from app.api.payment import router as payment_router

from app.models.account import Account
from app.services.worker import run_worker


app = FastAPI()

Base.metadata.create_all(bind=engine)

worker_thread = threading.Thread(target=run_worker, daemon=True)
worker_thread.start()

app.include_router(green_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(payment_router)


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/test-db")
def test_db():
    db = SessionLocal()
    try:
        unique_email = f"test_{int(datetime.utcnow().timestamp())}@test.com"

        acc = Account(
            email=unique_email,
            password_hash="test_hash_123"
        )

        db.add(acc)
        db.commit()
        db.refresh(acc)

        return {
            "status": "created",
            "id": acc.id,
            "email": acc.email
        }
    finally:
        db.close()
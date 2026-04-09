from fastapi import FastAPI
import threading

from app.models import *
from app.core.db import Base, engine

from app.webhook_green import router as green_router

from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.account import router as account_router
from app.api.payment import router as payment_router

from app.models.webhook_event import WebhookEvent
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
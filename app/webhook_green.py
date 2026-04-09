from fastapi import APIRouter, Request
import traceback

from app.core.db import SessionLocal
from app.models.account import Account
from app.models.webhook_event import WebhookEvent

router = APIRouter()


@router.get("/webhook/green")
def webhook_green_get():
    return {"status": "green webhook get ok"}


@router.post("/webhook/green")
async def webhook_green_post(request: Request):
    db = SessionLocal()

    try:
        data = await request.json()
        print("WEBHOOK DATA:", data)

        if data.get("typeWebhook") != "incomingMessageReceived":
            print("IGNORED: not incomingMessageReceived")
            return {"status": "ignored"}

        instance_id = data.get("instanceData", {}).get("idInstance") or data.get("instanceId")
        message_id = data.get("idMessage")

        sender_data = data.get("senderData", {})
        chat_id = sender_data.get("chatId")

        print("PARSED:", {
            "instance_id": instance_id,
            "message_id": message_id,
            "chat_id": chat_id
        })

        if not instance_id or not message_id:
            print("BAD DATA: missing instance_id or message_id")
            return {"status": "bad_data"}

        instance_id = str(instance_id)
        message_id = str(message_id)

        account = (
            db.query(Account)
            .filter(Account.green_id_instance == instance_id)
            .first()
        )

        if not account:
            print("ACCOUNT NOT FOUND:", instance_id)
            return {"status": "account_not_found"}

        print("ACCOUNT FOUND:", {
            "id": account.id,
            "email": account.email,
            "subscription_active": account.subscription_active,
            "is_paused": account.is_paused
        })

        if account.is_paused:
            print("BOT PAUSED")
            return {"status": "bot_paused"}

        if not account.subscription_active:
            print("SUBSCRIPTION INACTIVE")
            return {"status": "subscription_inactive"}

        existing = (
            db.query(WebhookEvent)
            .filter(
                WebhookEvent.instance_id == instance_id,
                WebhookEvent.external_message_id == message_id
            )
            .first()
        )

        if existing:
            print("DUPLICATE MESSAGE:", message_id)
            return {"status": "duplicate"}

        event = WebhookEvent(
            instance_id=instance_id,
            external_message_id=message_id,
            chat_id=chat_id,
            payload_json=data,
            status="pending"
        )

        db.add(event)
        db.commit()

        print("EVENT QUEUED:", {
            "instance_id": instance_id,
            "message_id": message_id,
            "chat_id": chat_id
        })

        return {"status": "queued"}

    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "detail": str(e)}

    finally:
        db.close()
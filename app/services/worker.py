import time
import traceback
from datetime import datetime, timedelta, UTC

from app.core.db import SessionLocal
from app.models.webhook_event import WebhookEvent
from app.models.account import Account
from app.services.green_api import send_message


AUTO_REPLY_TEXT = "Подскажите, пожалуйста: вас интересует покупка, аренда или продажа недвижимости?"


def extract_text_from_event(payload: dict) -> str:
    try:
        message_data = payload.get("messageData", {})
        text_message_data = message_data.get("textMessageData", {})
        return (text_message_data.get("textMessage") or "").strip()
    except Exception:
        return ""


def should_skip_duplicate_reply(db, event: WebhookEvent) -> bool:
    """
    Защита от дублей:
    если по этому chat_id уже был успешно обработанный auto-reply
    за последние 60 секунд, новый такой же не отправляем.
    """
    if not event.chat_id:
        return False

    one_minute_ago = datetime.now(UTC) - timedelta(seconds=60)

    recent_done = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.chat_id == event.chat_id,
            WebhookEvent.status == "done",
            WebhookEvent.processed_at.isnot(None),
            WebhookEvent.processed_at >= one_minute_ago,
            WebhookEvent.id != event.id,
        )
        .order_by(WebhookEvent.processed_at.desc())
        .first()
    )

    return recent_done is not None


def process_one_event(db, event: WebhookEvent):
    print(f"PROCESSING EVENT: id={event.id}, chat_id={event.chat_id}, retry_count={event.retry_count}")

    payload = event.payload_json or {}
    incoming_text = extract_text_from_event(payload)
    print(f"INCOMING TEXT: {incoming_text}")

    account = (
        db.query(Account)
        .filter(Account.green_id_instance == int(event.instance_id))
        .first()
    )

    if not account:
        raise Exception(f"Account not found for instance_id={event.instance_id}")

    if not account.green_api_token:
        raise Exception("green_api_token is empty")

    if should_skip_duplicate_reply(db, event):
        print(f"SKIP DUPLICATE REPLY: event_id={event.id}, chat_id={event.chat_id}")
        event.status = "done"
        event.processed_at = datetime.now(UTC)
        db.commit()
        return

    reply_text = AUTO_REPLY_TEXT
    print(f"BOT REPLY: {reply_text}")

    send_result = send_message(
        id_instance=str(account.green_id_instance),
        api_token=account.green_api_token,
        chat_id=event.chat_id,
        message=reply_text,
    )

    print(f"SEND RESULT: {send_result}")

    event.status = "done"
    event.processed_at = datetime.now(UTC)
    db.commit()

    print(f"EVENT DONE: id={event.id}")


def run_worker():
    print("🚀 Worker started")

    while True:
        db = SessionLocal()

        try:
            events = (
                db.query(WebhookEvent)
                .filter(
                    WebhookEvent.status.in_(["pending", "failed"]),
                    WebhookEvent.retry_count < 3,
                )
                .order_by(WebhookEvent.created_at.asc())
                .limit(10)
                .all()
            )

            if not events:
                db.close()
                time.sleep(2)
                continue

            for event in events:
                try:
                    event.status = "processing"
                    db.commit()

                    process_one_event(db, event)

                except Exception as e:
                    traceback.print_exc()

                    db.rollback()

                    fresh_event = db.query(WebhookEvent).filter(WebhookEvent.id == event.id).first()
                    if fresh_event:
                        fresh_event.retry_count = (fresh_event.retry_count or 0) + 1
                        fresh_event.status = "failed"
                        fresh_event.error_text = str(e)[:1000]
                        fresh_event.processed_at = datetime.now(UTC)
                        db.commit()

                    print(f"SEND FAILED: event_id={event.id}, error={e}")

        except Exception:
            traceback.print_exc()

        finally:
            db.close()

        time.sleep(2)
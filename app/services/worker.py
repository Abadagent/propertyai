import time
import traceback
from datetime import datetime, timedelta

from app.core.db import SessionLocal
from app.models.webhook_event import WebhookEvent
from app.models.account import Account
from app.services.chat_logic import process_message
from app.services.green_api import send_message


def send_with_retry(account, chat_id, text, retries=3):
    last_error = None

    for attempt in range(retries):
        try:
            send_message(
                id_instance=str(account.green_id_instance),
                api_token=account.green_api_token,
                chat_id=chat_id,
                text=text
            )
            return True
        except Exception as e:
            last_error = e
            time.sleep(1 * (attempt + 1))

    raise last_error


def extract_text_from_payload(payload):
    sender_data = payload.get("senderData", {})
    message_data = payload.get("messageData", {})

    chat_id = sender_data.get("chatId")

    text = None
    if message_data.get("typeMessage") == "textMessage":
        text = message_data.get("textMessageData", {}).get("textMessage")
    elif message_data.get("typeMessage") == "extendedTextMessage":
        text = message_data.get("extendedTextMessageData", {}).get("text")

    return chat_id, text


def is_duplicate_message(db, current_event, green_instance_id, chat_id, text):
    five_seconds_ago = datetime.utcnow() - timedelta(seconds=5)

    recent = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.instance_id == str(green_instance_id),
            WebhookEvent.chat_id == chat_id,
            WebhookEvent.created_at >= five_seconds_ago,
            WebhookEvent.id != current_event.id,
            WebhookEvent.status.in_(["done", "processing"])
        )
        .all()
    )

    current_text = text.strip().lower()

    for r in recent:
        _, old_text = extract_text_from_payload(r.payload_json)
        if old_text and old_text.strip().lower() == current_text:
            return True

    return False


def run_worker():
    print("🚀 Worker started")

    while True:
        db = SessionLocal()

        try:
            events = (
                db.query(WebhookEvent)
                .filter(
                    WebhookEvent.status.in_(["pending", "failed"]),
                    WebhookEvent.retry_count < 3
                )
                .order_by(WebhookEvent.created_at.asc())
                .limit(10)
                .all()
            )

            if not events:
                time.sleep(2)
                continue

            for event in events:
                try:
                    if event.status != "processing":
                        event.status = "processing"
                        db.commit()
                        db.refresh(event)

                    account = (
                        db.query(Account)
                        .filter(Account.green_id_instance == str(event.instance_id))
                        .first()
                    )

                    if not account:
                        event.status = "failed"
                        event.error_text = f"account_not_found: {event.instance_id}"
                        event.retry_count += 1
                        if event.retry_count >= 3:
                            event.processed_at = datetime.utcnow()
                        db.commit()
                        continue

                    if account.is_paused:
                        event.status = "done"
                        event.error_text = "bot_paused"
                        event.processed_at = datetime.utcnow()
                        db.commit()
                        continue

                    if not account.subscription_active:
                        event.status = "done"
                        event.error_text = "subscription_inactive"
                        event.processed_at = datetime.utcnow()
                        db.commit()
                        continue

                    chat_id, text = extract_text_from_payload(event.payload_json)

                    if not chat_id or not text:
                        event.status = "done"
                        event.error_text = None
                        event.processed_at = datetime.utcnow()
                        db.commit()
                        continue

                    if is_duplicate_message(
                        db=db,
                        current_event=event,
                        green_instance_id=event.instance_id,
                        chat_id=chat_id,
                        text=text
                    ):
                        event.status = "done"
                        event.error_text = "duplicate_message"
                        event.processed_at = datetime.utcnow()
                        db.commit()
                        continue

                    if account.messages_used >= account.messages_limit:
                        try:
                            send_with_retry(
                                account,
                                chat_id,
                                "❌ Лимит сообщений исчерпан. Обратитесь к менеджеру."
                            )
                            event.status = "done"
                            event.error_text = "limit_reached"
                            event.processed_at = datetime.utcnow()
                            db.commit()
                        except Exception as e:
                            event.status = "failed"
                            event.error_text = f"limit_send_failed: {str(e)}"
                            event.retry_count += 1
                            if event.retry_count >= 3:
                                event.processed_at = datetime.utcnow()
                            db.commit()
                        continue

                    result = process_message(
                        db=db,
                        account=account,
                        phone=chat_id,
                        text=text
                    )

                    reply = result.get("reply") if isinstance(result, dict) else None

                    if not reply:
                        reply = "Напишите, пожалуйста, что вас интересует 🙂"

                    try:
                        send_with_retry(account, chat_id, reply)

                        account.messages_used += 1

                        event.status = "done"
                        event.error_text = None
                        event.retry_count = 0
                        event.processed_at = datetime.utcnow()

                        db.commit()

                    except Exception as e:
                        event.status = "failed"
                        event.error_text = f"send_failed: {str(e)}"
                        event.retry_count += 1
                        if event.retry_count >= 3:
                            event.processed_at = datetime.utcnow()
                        db.commit()

                except Exception as e:
                    event.status = "failed"
                    event.error_text = str(e)
                    event.retry_count += 1
                    if event.retry_count >= 3:
                        event.processed_at = datetime.utcnow()
                    db.commit()
                    traceback.print_exc()

        except Exception:
            traceback.print_exc()

        finally:
            db.close()

        time.sleep(2)


if __name__ == "__main__":
    run_worker()
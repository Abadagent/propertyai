print("WORKER FILE LOADED")

import time
import traceback
from datetime import datetime, timedelta, UTC

from sqlalchemy import or_

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

    type_webhook = payload.get("typeWebhook")
    if type_webhook != "incomingMessageReceived":
        print(f"SKIP NON-INCOMING: event_id={event.id}, typeWebhook={type_webhook}")
        event.status = "done"
        event.processed_at = datetime.now(UTC)
        event.error_text = None
        db.commit()
        return

    incoming_text = extract_text_from_event(payload)
    print(f"INCOMING TEXT: {incoming_text}")

    if not event.instance_id:
        raise Exception("event.instance_id is empty")

    print(f"INSTANCE_ID TYPE: {type(event.instance_id)} VALUE: {event.instance_id}")

    instance_id_str = str(event.instance_id).strip()
    print(f"INSTANCE_ID_STR TYPE: {type(instance_id_str)} VALUE: {instance_id_str}")
    print(f"LOOKING ACCOUNT BY instance_id={instance_id_str}")

    account = (
        db.query(Account)
        .filter(Account.green_id_instance == instance_id_str)
        .first()
    )

    if not account:
        raise Exception(f"Account not found for instance_id={instance_id_str}")

    if not account.green_api_token:
        raise Exception("green_api_token is empty")

    if not event.chat_id:
        raise Exception("event.chat_id is empty")

    if should_skip_duplicate_reply(db, event):
        print(f"SKIP DUPLICATE REPLY: event_id={event.id}, chat_id={event.chat_id}")
        event.status = "done"
        event.processed_at = datetime.now(UTC)
        event.error_text = None
        db.commit()
        return

    reply_text = AUTO_REPLY_TEXT
    print(f"BOT REPLY: {reply_text}")

    send_result = send_message(
        id_instance=instance_id_str,
        api_token=account.green_api_token,
        chat_id=event.chat_id,
        message=reply_text,
    )

    print(f"SEND RESULT: {send_result}")

    event.status = "done"
    event.processed_at = datetime.now(UTC)
    event.error_text = None
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
                    or_(
                        WebhookEvent.retry_count.is_(None),
                        WebhookEvent.retry_count < 3,
                    ),
                )
                .order_by(WebhookEvent.created_at.asc())
                .limit(10)
                .all()
            )

            print(f"FOUND EVENTS: {len(events)}")

            if not events:
                db.close()
                time.sleep(2)
                continue

            for event in events:
                try:
                    fresh_event = db.query(WebhookEvent).filter(WebhookEvent.id == event.id).first()
                    if not fresh_event:
                        print(f"EVENT NOT FOUND: id={event.id}")
                        continue

                    if fresh_event.status not in ("pending", "failed"):
                        print(f"SKIP EVENT WITH STATUS={fresh_event.status}: id={fresh_event.id}")
                        continue

                    fresh_event.status = "processing"
                    fresh_event.error_text = None
                    db.commit()

                    process_one_event(db, fresh_event)

                except Exception as e:
                    traceback.print_exc()
                    db.rollback()

                    failed_event = db.query(WebhookEvent).filter(WebhookEvent.id == event.id).first()
                    if failed_event:
                        failed_event.retry_count = (failed_event.retry_count or 0) + 1
                        failed_event.status = "failed"
                        failed_event.error_text = str(e)[:1000]
                        db.commit()

                    print(f"SEND FAILED: event_id={event.id}, error={e}")

        except Exception:
            traceback.print_exc()

        finally:
            db.close()

        time.sleep(2)


if __name__ == "__main__":
    run_worker()
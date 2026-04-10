print("WORKER FILE LOADED")

import time
import traceback
from datetime import datetime, UTC

from sqlalchemy import or_, bindparam, String

from app.core.db import SessionLocal
from app.models.webhook_event import WebhookEvent
from app.models.account import Account
from app.services.green_api import send_message
from app.services.chat_logic import process_message


def extract_text_from_event(payload: dict) -> str:
    try:
        message_data = payload.get("messageData", {})
        text_message_data = message_data.get("textMessageData", {})
        return (text_message_data.get("textMessage") or "").strip()
    except Exception:
        return ""


def process_one_event(db, event: WebhookEvent):
    print(
        f"PROCESSING EVENT: id={event.id}, chat_id={event.chat_id}, retry_count={event.retry_count}",
        flush=True,
    )

    payload = event.payload_json or {}

    type_webhook = payload.get("typeWebhook")
    if type_webhook != "incomingMessageReceived":
        print(
            f"SKIP NON-INCOMING: event_id={event.id}, typeWebhook={type_webhook}",
            flush=True,
        )
        event.status = "done"
        event.processed_at = datetime.now(UTC)
        event.error_text = None
        db.commit()
        return

    incoming_text = extract_text_from_event(payload)
    print(f"INCOMING TEXT: {incoming_text}", flush=True)

    if not event.instance_id:
        raise Exception("event.instance_id is empty")

    instance_id_str = str(event.instance_id).strip()
    print(
        f"INSTANCE_ID_STR TYPE: {type(instance_id_str)} VALUE: {instance_id_str}",
        flush=True,
    )

    account = (
        db.query(Account)
        .filter(
            Account.green_id_instance == bindparam(
                "green_id_instance_param",
                value=instance_id_str,
                type_=String(),
            )
        )
        .first()
    )

    if not account:
        raise Exception(f"Account not found for instance_id={instance_id_str}")

    if not account.green_api_token:
        raise Exception("green_api_token is empty")

    if not event.chat_id:
        raise Exception("event.chat_id is empty")

    logic_result = process_message(
        db=db,
        account=account,
        phone=event.chat_id,
        text=incoming_text,
    )

    print(f"LOGIC RESULT: {logic_result}", flush=True)

    reply_text = (logic_result or {}).get("reply")
    if not reply_text:
        print(f"NO REPLY GENERATED: event_id={event.id}", flush=True)
        event.status = "done"
        event.processed_at = datetime.now(UTC)
        event.error_text = None
        db.commit()
        return

    print(f"BOT REPLY: {reply_text}", flush=True)

    send_result = send_message(
        id_instance=instance_id_str,
        api_token=account.green_api_token,
        chat_id=event.chat_id,
        message=reply_text,
    )

    print(f"SEND RESULT: {send_result}", flush=True)

    event.status = "done"
    event.processed_at = datetime.now(UTC)
    event.error_text = None
    db.commit()

    print(f"EVENT DONE: id={event.id}", flush=True)


def run_worker():
    print("🚀 Worker started", flush=True)

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

            print(f"FOUND EVENTS: {len(events)}", flush=True)

            if not events:
                db.close()
                time.sleep(2)
                continue

            for event in events:
                try:
                    fresh_event = (
                        db.query(WebhookEvent)
                        .filter(WebhookEvent.id == event.id)
                        .first()
                    )

                    if not fresh_event:
                        print(f"EVENT NOT FOUND: id={event.id}", flush=True)
                        continue

                    if fresh_event.status not in ("pending", "failed"):
                        print(
                            f"SKIP EVENT WITH STATUS={fresh_event.status}: id={fresh_event.id}",
                            flush=True,
                        )
                        continue

                    fresh_event.status = "processing"
                    fresh_event.error_text = None
                    db.commit()

                    process_one_event(db, fresh_event)

                except Exception as e:
                    traceback.print_exc()
                    db.rollback()

                    failed_event = (
                        db.query(WebhookEvent)
                        .filter(WebhookEvent.id == event.id)
                        .first()
                    )

                    if failed_event:
                        failed_event.retry_count = (failed_event.retry_count or 0) + 1
                        failed_event.status = "failed"
                        failed_event.error_text = str(e)[:1000]
                        failed_event.processed_at = datetime.now(UTC)
                        db.commit()

                    print(f"SEND FAILED: event_id={event.id}, error={e}", flush=True)

        except Exception:
            traceback.print_exc()

        finally:
            db.close()

        time.sleep(2)


if __name__ == "__main__":
    run_worker()
import requests
from datetime import datetime


TELEGRAM_BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN"


def parse_chat_ids(chat_ids_raw: str):
    if not chat_ids_raw:
        return []

    return [item.strip() for item in chat_ids_raw.split(",") if item.strip()]


def format_datetime(dt):
    if not dt:
        return "-"

    return dt.strftime("%d.%m.%Y %H:%M")


def build_lead_message(account, lead):
    account_name = account.name if account and account.name else "-"
    created_at = format_datetime(getattr(lead, "created_at", None))

    return (
        "🔥 Новый лид\n\n"
        f"Аккаунт: {account_name}\n"
        f"Время: {created_at}\n\n"
        f"Имя: {lead.name or '-'}\n"
        f"Телефон: {lead.phone or '-'}\n\n"
        f"Тип сделки: {lead.request_type or '-'}\n"
        f"Тип объекта: {lead.property_type or '-'}\n"
        f"Район: {lead.district or '-'}\n"
        f"Комнаты: {lead.rooms or '-'}\n"
        f"Бюджет: {lead.budget or '-'}\n"
        f"Цель: {lead.purpose or '-'}\n\n"
        f"Lead ID: {lead.id or '-'}"
    )


def send_message_to_telegram(chat_id: str, text: str):
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN":
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
            },
            timeout=10,
        )
    except Exception:
        pass


def send_lead_to_telegram(account, lead):
    if not account:
        return

    chat_ids = parse_chat_ids(account.telegram_chat_ids)

    if not chat_ids:
        return

    text = build_lead_message(account, lead)

    for chat_id in chat_ids:
        send_message_to_telegram(chat_id, text)
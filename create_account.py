from datetime import datetime

from app.core.db import SessionLocal
from app.models.account import Account


db = SessionLocal()

# создаём тестовый аккаунт
account = Account(
    name="Test Agency",
    whatsapp_phone="77771234567",
    whatsapp_connected=True,
    bot_paused=False,
    subscription_active_until=datetime(2099, 1, 1),
    telegram_chat_ids="PASTE_YOUR_CHAT_ID"
)

db.add(account)
db.commit()

print("✅ Account создан")

db.close()
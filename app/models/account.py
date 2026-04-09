from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    company_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    is_paused = Column(Boolean, default=False)
    manager_connected = Column(Boolean, default=False)

    plan_name = Column(String, default="basic")
    billing_status = Column(String, default="pending_payment")
    subscription_active = Column(Boolean, default=False)
    paid_until = Column(DateTime, nullable=True)

    # 🔥 ЛИМИТЫ
    messages_used = Column(Integer, default=0)
    messages_limit = Column(Integer, default=100)

    green_id_instance = Column(String, unique=True, index=True, nullable=True)
    green_api_token = Column(String, nullable=True)
    green_connected = Column(Boolean, default=False)
    green_status = Column(String, default="not_connected")
    green_phone = Column(String, nullable=True)

    onboarding_completed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="account")
    leads = relationship("Lead", back_populates="account")
    payments = relationship("Payment", back_populates="account")
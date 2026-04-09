from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.db import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    amount = Column(Integer, nullable=False)
    currency = Column(String, default="KZT", nullable=False)

    status = Column(String, default="pending", nullable=False)
    provider = Column(String, default="manual", nullable=False)

    plan_name = Column(String, default="basic", nullable=False)
    period_days = Column(Integer, default=30, nullable=False)

    external_payment_id = Column(String, nullable=True)
    payment_url = Column(Text, nullable=True)

    comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    account = relationship("Account", back_populates="payments")
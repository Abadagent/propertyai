from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.db import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    phone = Column(String, index=True, nullable=False)

    state = Column(String, default="new", nullable=False)

    request_type = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    district = Column(String, nullable=True)
    rooms = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    purpose = Column(String, nullable=True)
    name = Column(String, nullable=True)

    lead_sent = Column(Boolean, default=False)
    manager_connected = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="conversations")
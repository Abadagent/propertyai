from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, Text, UniqueConstraint, JSON, Integer

from app.core.db import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    instance_id = Column(String, nullable=False)
    external_message_id = Column(String, nullable=False)
    chat_id = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=False)

    status = Column(String, default="pending")
    error_text = Column(Text, nullable=True)

    retry_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("instance_id", "external_message_id", name="uix_instance_message"),
    )
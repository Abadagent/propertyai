from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.db import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    account_id = Column(Integer, ForeignKey("accounts.id"))

    name = Column(String)
    phone = Column(String)

    deal_type = Column(String)
    property_type = Column(String)
    district = Column(String)
    rooms = Column(String)
    budget = Column(String)
    goal = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="leads")
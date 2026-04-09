from pydantic import BaseModel


class LeadCreate(BaseModel):
    name: str | None = None
    phone: str | None = None

    request_type: str | None = None
    property_type: str | None = None
    district: str | None = None
    rooms: str | None = None
    budget: str | None = None
    purpose: str | None = None
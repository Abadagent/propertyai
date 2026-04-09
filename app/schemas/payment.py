from pydantic import BaseModel

class ActivateSubscriptionRequest(BaseModel):
    account_id: int
    days: int = 30
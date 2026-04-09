from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    phone: str
    text: str
    token: str
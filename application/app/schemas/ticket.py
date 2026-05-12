from pydantic import BaseModel
from typing import List


class UserMessage(BaseModel):
    text: str


class ReassignmentRequest(BaseModel):
    new_departments: List[str]  


class MessageResponse(BaseModel):
    id: int
    ticket_id: int
    sender: str
    text: str

    class Config:
        from_attributes = True

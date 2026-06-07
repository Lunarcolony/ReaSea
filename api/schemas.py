from pydantic import BaseModel, EmailStr
from typing import Optional, List


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PreferencesUpdate(BaseModel):
    topic_slugs: List[str]
    research_role: Optional[str] = None


class EventItem(BaseModel):
    paper_id: int
    event_type: str
    read_time_seconds: Optional[int] = None


class EventsBatch(BaseModel):
    events: List[EventItem]

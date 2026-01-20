from datetime import datetime
from pydantic import BaseModel


class User(BaseModel):
    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_blocked: bool = False
    created_at: datetime | None = None
    last_message_at: datetime | None = None


class Ticket(BaseModel):
    id: int
    user_id: int
    status: str = "open"
    created_at: datetime | None = None
    closed_at: datetime | None = None


class Message(BaseModel):
    id: int
    ticket_id: int
    user_id: int
    user_message_id: int | None = None
    admin_message_id: int | None = None
    direction: str
    created_at: datetime | None = None


class QuickReply(BaseModel):
    id: int
    shortcut: str
    text: str


class UserStats(BaseModel):
    message_count: int = 0
    ticket_count: int = 0


class Stats(BaseModel):
    total_users: int = 0
    active_today: int = 0
    open_tickets: int = 0
    closed_tickets: int = 0
    avg_response_time_minutes: float | None = None
    messages_last_7_days: list[tuple[str, int]] = []

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class SupportTicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicket(SQLModel, table=True):
    __tablename__ = "support_tickets"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    created_by_user_id: int = Field(foreign_key="user.id", index=True)
    order_id: Optional[int] = Field(default=None, foreign_key="orders.id", index=True)
    return_request_id: Optional[int] = Field(default=None, foreign_key="return_requests.id", index=True)
    conversation_id: Optional[int] = Field(default=None, index=True)
    subject: str = Field(max_length=255)
    description: str = Field(default="", max_length=4000)
    status: SupportTicketStatus = Field(default=SupportTicketStatus.OPEN)
    priority: str = Field(default="normal", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

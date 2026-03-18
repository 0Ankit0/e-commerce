from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class SupportTicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    WAITING_ON_INTERNAL = "waiting_on_internal"
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
    assigned_to_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    first_response_due_at: Optional[datetime] = Field(default=None)
    resolution_due_at: Optional[datetime] = Field(default=None)
    first_responded_at: Optional[datetime] = Field(default=None)
    resolved_at: Optional[datetime] = Field(default=None)
    closed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SupportTicketComment(SQLModel, table=True):
    __tablename__ = "support_ticket_comments"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="support_tickets.id", index=True)
    author_user_id: int = Field(foreign_key="user.id", index=True)
    body: str = Field(max_length=4000)
    is_internal: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)


class SupportTicketEvent(SQLModel, table=True):
    __tablename__ = "support_ticket_events"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: int = Field(foreign_key="support_tickets.id", index=True)
    actor_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    event_type: str = Field(max_length=80, index=True)
    message: str = Field(default="", max_length=500)
    payload_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)

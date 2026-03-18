from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.orders.models import Order, ReturnRequest
from src.apps.support.models import SupportTicket, SupportTicketStatus

router = APIRouter()


class SupportTicketCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    description: str = ""
    order_id: str | None = None
    return_request_id: str | None = None
    conversation_id: str | None = None
    priority: str = "normal"


class SupportTicketUpdateRequest(BaseModel):
    status: SupportTicketStatus


@router.post("/support/tickets", status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: SupportTicketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order_id = decode_id_or_404(payload.order_id) if payload.order_id else None
    return_request_id = decode_id_or_404(payload.return_request_id) if payload.return_request_id else None
    if order_id:
        order = await db.get(Order, order_id)
        if order is None or order.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if return_request_id:
        return_request = await db.get(ReturnRequest, return_request_id)
        if return_request is None or return_request.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return request not found")
    ticket = SupportTicket(
        created_by_user_id=current_user.id,
        order_id=order_id,
        return_request_id=return_request_id,
        conversation_id=decode_id_or_404(payload.conversation_id) if payload.conversation_id else None,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return {"ticket_id": encode_id(ticket.id or 0)}


@router.get("/support/tickets")
async def list_my_tickets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tickets = (
        await db.execute(select(SupportTicket).where(SupportTicket.created_by_user_id == current_user.id).order_by(SupportTicket.created_at.desc()))
    ).scalars().all()
    return {"items": [_serialize_ticket(ticket) for ticket in tickets], "total": len(tickets)}


@router.get("/admin/support/tickets")
async def list_support_tickets(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    tickets = (await db.execute(select(SupportTicket).order_by(SupportTicket.created_at.desc()))).scalars().all()
    return {"items": [_serialize_ticket(ticket) for ticket in tickets], "total": len(tickets)}


@router.post("/admin/support/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    payload: SupportTicketUpdateRequest,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    ticket = await db.get(SupportTicket, decode_id_or_404(ticket_id))
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    ticket.status = payload.status
    ticket.updated_at = datetime.utcnow()
    await db.commit()
    return {"ticket": _serialize_ticket(ticket)}


def _serialize_ticket(ticket: SupportTicket) -> dict[str, object]:
    return {
        "id": encode_id(ticket.id or 0),
        "created_by_user_id": encode_id(ticket.created_by_user_id),
        "order_id": encode_id(ticket.order_id) if ticket.order_id else None,
        "return_request_id": encode_id(ticket.return_request_id) if ticket.return_request_id else None,
        "conversation_id": encode_id(ticket.conversation_id) if ticket.conversation_id else None,
        "subject": ticket.subject,
        "description": ticket.description,
        "status": ticket.status.value,
        "priority": ticket.priority,
        "created_at": ticket.created_at.isoformat(),
    }

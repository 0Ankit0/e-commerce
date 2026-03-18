from __future__ import annotations

import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.time import utc_now
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.orders.models import Order, ReturnRequest
from src.apps.support.models import SupportTicket, SupportTicketComment, SupportTicketEvent, SupportTicketStatus

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
    assignee_user_id: str | None = None


class SupportTicketCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    is_internal: bool = False


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
        first_response_due_at=utc_now() + timedelta(hours=4),
        resolution_due_at=utc_now() + timedelta(hours=48),
    )
    db.add(ticket)
    await db.flush()
    db.add(
        SupportTicketEvent(
            ticket_id=ticket.id or 0,
            actor_user_id=current_user.id,
            event_type="ticket.created",
            message="Support ticket created",
            payload_json=json.dumps({"priority": ticket.priority}),
        )
    )
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


@router.get("/support/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await db.get(SupportTicket, decode_id_or_404(ticket_id))
    if ticket is None or ticket.created_by_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    comments = (
        await db.execute(
            select(SupportTicketComment).where(
                SupportTicketComment.ticket_id == ticket.id,
                SupportTicketComment.is_internal == False,  # noqa: E712
            ).order_by(SupportTicketComment.created_at.asc())
        )
    ).scalars().all()
    events = (
        await db.execute(select(SupportTicketEvent).where(SupportTicketEvent.ticket_id == ticket.id).order_by(SupportTicketEvent.created_at.asc()))
    ).scalars().all()
    return {
        "ticket": _serialize_ticket(ticket),
        "comments": [_serialize_comment(comment) for comment in comments],
        "timeline": [_serialize_event(event) for event in events],
    }


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
    old_status = ticket.status
    ticket.status = payload.status
    ticket.assigned_to_user_id = decode_id_or_404(payload.assignee_user_id) if payload.assignee_user_id else ticket.assigned_to_user_id
    ticket.updated_at = utc_now()
    if ticket.first_responded_at is None and ticket.status != SupportTicketStatus.OPEN:
        ticket.first_responded_at = utc_now()
    if payload.status == SupportTicketStatus.RESOLVED:
        ticket.resolved_at = utc_now()
    if payload.status == SupportTicketStatus.CLOSED:
        ticket.closed_at = utc_now()
    db.add(
        SupportTicketEvent(
            ticket_id=ticket.id or 0,
            event_type="ticket.status_changed",
            message=f"Status updated from {old_status.value} to {ticket.status.value}",
            payload_json=json.dumps(
                {
                    "old_status": old_status.value,
                    "new_status": ticket.status.value,
                    "assignee_user_id": ticket.assigned_to_user_id,
                }
            ),
        )
    )
    await db.commit()
    return {"ticket": _serialize_ticket(ticket)}


@router.post("/support/tickets/{ticket_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_ticket_comment(
    ticket_id: str,
    payload: SupportTicketCommentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticket = await db.get(SupportTicket, decode_id_or_404(ticket_id))
    if ticket is None or ticket.created_by_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    comment = SupportTicketComment(
        ticket_id=ticket.id or 0,
        author_user_id=current_user.id,
        body=payload.body,
        is_internal=False,
    )
    ticket.updated_at = utc_now()
    db.add(comment)
    db.add(
        SupportTicketEvent(
            ticket_id=ticket.id or 0,
            actor_user_id=current_user.id,
            event_type="ticket.comment_added",
            message="Customer added a comment",
            payload_json=json.dumps({"is_internal": False}),
        )
    )
    await db.commit()
    await db.refresh(comment)
    return {"comment": _serialize_comment(comment)}


@router.post("/admin/support/tickets/{ticket_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_admin_ticket_comment(
    ticket_id: str,
    payload: SupportTicketCommentRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    ticket = await db.get(SupportTicket, decode_id_or_404(ticket_id))
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    comment = SupportTicketComment(
        ticket_id=ticket.id or 0,
        author_user_id=current_user.id,
        body=payload.body,
        is_internal=payload.is_internal,
    )
    ticket.updated_at = utc_now()
    ticket.assigned_to_user_id = ticket.assigned_to_user_id or current_user.id
    if ticket.first_responded_at is None:
        ticket.first_responded_at = utc_now()
    db.add(comment)
    db.add(
        SupportTicketEvent(
            ticket_id=ticket.id or 0,
            actor_user_id=current_user.id,
            event_type="ticket.comment_added",
            message="Support agent added a comment",
            payload_json=json.dumps({"is_internal": payload.is_internal}),
        )
    )
    await db.commit()
    await db.refresh(comment)
    return {"comment": _serialize_comment(comment)}


@router.get("/admin/support/tickets/{ticket_id}")
async def get_admin_ticket_detail(
    ticket_id: str,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    ticket = await db.get(SupportTicket, decode_id_or_404(ticket_id))
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    comments = (
        await db.execute(select(SupportTicketComment).where(SupportTicketComment.ticket_id == ticket.id).order_by(SupportTicketComment.created_at.asc()))
    ).scalars().all()
    events = (
        await db.execute(select(SupportTicketEvent).where(SupportTicketEvent.ticket_id == ticket.id).order_by(SupportTicketEvent.created_at.asc()))
    ).scalars().all()
    return {
        "ticket": _serialize_ticket(ticket),
        "comments": [_serialize_comment(comment) for comment in comments],
        "timeline": [_serialize_event(event) for event in events],
    }


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
        "assigned_to_user_id": encode_id(ticket.assigned_to_user_id) if ticket.assigned_to_user_id else None,
        "first_response_due_at": ticket.first_response_due_at.isoformat() if ticket.first_response_due_at else None,
        "resolution_due_at": ticket.resolution_due_at.isoformat() if ticket.resolution_due_at else None,
        "first_responded_at": ticket.first_responded_at.isoformat() if ticket.first_responded_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "created_at": ticket.created_at.isoformat(),
    }


def _serialize_comment(comment: SupportTicketComment) -> dict[str, object]:
    return {
        "id": encode_id(comment.id or 0),
        "author_user_id": encode_id(comment.author_user_id),
        "body": comment.body,
        "is_internal": comment.is_internal,
        "created_at": comment.created_at.isoformat(),
    }


def _serialize_event(event: SupportTicketEvent) -> dict[str, object]:
    return {
        "id": encode_id(event.id or 0),
        "actor_user_id": encode_id(event.actor_user_id) if event.actor_user_id else None,
        "event_type": event.event_type,
        "message": event.message,
        "payload": json.loads(event.payload_json or "{}"),
        "created_at": event.created_at.isoformat(),
    }

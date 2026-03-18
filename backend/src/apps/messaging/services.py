from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.messaging.models import (
    ChatAttachment,
    ChatConversation,
    ChatConversationType,
    ChatDevice,
    ChatKeyBackup,
    ChatMessageEnvelope,
    ChatOneTimePreKey,
    ChatParticipant,
    ChatParticipantRole,
    ChatReadReceipt,
    ChatReport,
    ChatSignedPreKey,
)
from src.apps.orders.models import Order
from src.apps.vendors.models import Vendor
from src.apps.websocket.manager import manager


async def get_active_device_or_404(device_id: str, user_id: int, db: AsyncSession) -> ChatDevice:
    device = (
        await db.execute(
            select(ChatDevice).where(
                ChatDevice.device_id == device_id,
                ChatDevice.user_id == user_id,
                ChatDevice.is_active == True,  # noqa: E712
            )
        )
    ).scalars().first()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat device not found")
    return device


async def get_conversation_or_404(conversation_id: int, db: AsyncSession) -> ChatConversation:
    conversation = await db.get(ChatConversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


async def ensure_participant(conversation_id: int, user_id: int, db: AsyncSession) -> ChatParticipant:
    participant = (
        await db.execute(
            select(ChatParticipant).where(
                ChatParticipant.conversation_id == conversation_id,
                ChatParticipant.user_id == user_id,
            )
        )
    ).scalars().first()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a conversation participant")
    return participant


async def create_order_conversation(order: Order, vendor: Vendor, created_by_user_id: int, db: AsyncSession) -> ChatConversation:
    existing = (
        await db.execute(
            select(ChatConversation).where(
                ChatConversation.order_id == order.id,
                ChatConversation.vendor_id == vendor.id,
            )
        )
    ).scalars().first()
    if existing:
        return existing
    conversation = ChatConversation(
        conversation_type=ChatConversationType.ORDER,
        order_id=order.id,
        vendor_id=vendor.id,
        created_by_user_id=created_by_user_id,
    )
    db.add(conversation)
    await db.flush()
    db.add(ChatParticipant(conversation_id=conversation.id, user_id=order.user_id, role=ChatParticipantRole.CUSTOMER))
    db.add(ChatParticipant(conversation_id=conversation.id, user_id=vendor.owner_user_id, role=ChatParticipantRole.VENDOR))
    return conversation


async def send_encrypted_message(
    *,
    conversation_id: int,
    sender_user_id: int,
    sender_device: ChatDevice,
    ciphertext: str,
    header: dict[str, object],
    attachments: list[dict[str, object]],
    db: AsyncSession,
) -> ChatMessageEnvelope:
    await ensure_participant(conversation_id, sender_user_id, db)
    envelope = ChatMessageEnvelope(
        conversation_id=conversation_id,
        sender_user_id=sender_user_id,
        sender_device_id=sender_device.id,
        ciphertext=ciphertext,
        header_json=json.dumps(header),
        attachment_manifest_json=json.dumps(attachments),
    )
    db.add(envelope)
    await db.flush()
    for attachment in attachments:
        db.add(
            ChatAttachment(
                message_id=envelope.id,
                blob_url=str(attachment.get("blob_url", "")),
                media_type=str(attachment.get("media_type", "application/octet-stream")),
                size_bytes=int(attachment.get("size_bytes", 0) or 0),
                encrypted_file_key=str(attachment.get("encrypted_file_key", "")),
                nonce=str(attachment.get("nonce", "")),
                sha256=str(attachment.get("sha256", "")),
            )
        )

    participants = (
        await db.execute(select(ChatParticipant).where(ChatParticipant.conversation_id == conversation_id))
    ).scalars().all()
    for participant in participants:
        if participant.user_id == sender_user_id:
            continue
        await manager.push_event(
            participant.user_id,
            "chat.message.envelope",
            {
                "conversation_id": conversation_id,
                "message_id": envelope.id,
                "sender_user_id": sender_user_id,
                "ciphertext": ciphertext,
                "header": header,
                "attachments": attachments,
            },
        )
    return envelope


async def get_prekey_bundle_for_user(target_user_id: int, db: AsyncSession) -> dict[str, object]:
    device = (
        await db.execute(
            select(ChatDevice).where(ChatDevice.user_id == target_user_id, ChatDevice.is_active == True)  # noqa: E712
        )
    ).scalars().first()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active chat device found")
    signed_prekey = (
        await db.execute(select(ChatSignedPreKey).where(ChatSignedPreKey.device_id == device.id).order_by(ChatSignedPreKey.id.desc()))
    ).scalars().first()
    one_time_prekey = (
        await db.execute(
            select(ChatOneTimePreKey).where(
                ChatOneTimePreKey.device_id == device.id,
                ChatOneTimePreKey.is_consumed == False,  # noqa: E712
            ).order_by(ChatOneTimePreKey.id.asc())
        )
    ).scalars().first()
    if one_time_prekey:
        one_time_prekey.is_consumed = True
    return {
        "device_id": device.device_id,
        "identity_key_public": device.identity_key_public,
        "signed_prekey_public": signed_prekey.public_key if signed_prekey else device.signed_prekey_public,
        "signed_prekey_signature": signed_prekey.signature if signed_prekey else device.signed_prekey_signature,
        "one_time_prekey_id": one_time_prekey.key_id if one_time_prekey else None,
        "one_time_prekey_public": one_time_prekey.public_key if one_time_prekey else None,
    }


async def save_key_backup(user_id: int, backup_blob: str, salt: str, metadata: dict[str, object], db: AsyncSession) -> ChatKeyBackup:
    backup = (await db.execute(select(ChatKeyBackup).where(ChatKeyBackup.user_id == user_id))).scalars().first()
    if backup is None:
        backup = ChatKeyBackup(user_id=user_id, backup_blob=backup_blob, salt=salt, metadata_json=json.dumps(metadata))
        db.add(backup)
    else:
        backup.backup_blob = backup_blob
        backup.salt = salt
        backup.metadata_json = json.dumps(metadata)
    await db.flush()
    return backup


async def list_conversation_messages(conversation_id: int, user_id: int, db: AsyncSession) -> list[ChatMessageEnvelope]:
    await ensure_participant(conversation_id, user_id, db)
    return (
        await db.execute(
            select(ChatMessageEnvelope).where(ChatMessageEnvelope.conversation_id == conversation_id).order_by(ChatMessageEnvelope.created_at.asc())
        )
    ).scalars().all()

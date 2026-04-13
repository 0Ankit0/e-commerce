from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.core.time import utc_now
from src.apps.iam.api.deps import get_current_active_superuser, get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.utils.hashid import decode_id_or_404, encode_id
from src.apps.messaging.models import (
    ChatAttachment,
    ChatConversation,
    ChatDevice,
    ChatKeyBackup,
    ChatMessageEnvelope,
    ChatOneTimePreKey,
    ChatParticipant,
    ChatReadReceipt,
    ChatReport,
    ChatSignedPreKey,
)
from src.apps.messaging.services import (
    create_order_conversation,
    get_active_device_or_404,
    get_conversation_or_404,
    get_prekey_bundle_for_user,
    list_conversation_messages,
    save_key_backup,
    send_encrypted_message,
)
from src.apps.orders.models import Order
from src.apps.vendors.models import Vendor

router = APIRouter()


class ChatDeviceRegisterRequest(BaseModel):
    device_id: str
    device_label: str = ""
    identity_key_public: str
    signed_prekey_public: str
    signed_prekey_signature: str


class SignedPreKeyRequest(BaseModel):
    key_id: int
    public_key: str
    signature: str


class OneTimePreKeyRequest(BaseModel):
    keys: list[dict[str, object]]


class ConversationCreateRequest(BaseModel):
    order_id: str
    vendor_id: str


class MessageSendRequest(BaseModel):
    device_id: str
    ciphertext: str
    header: dict[str, object] = Field(default_factory=dict)
    attachments: list[dict[str, object]] = Field(default_factory=list)


class BackupBlobRequest(BaseModel):
    backup_blob: str
    salt: str
    metadata: dict[str, object] = Field(default_factory=dict)


class ReportRequest(BaseModel):
    reason: str
    metadata: dict[str, object] = Field(default_factory=dict)


class MarkReadRequest(BaseModel):
    message_id: str
    device_id: str | None = None


class AttachmentManifestItem(BaseModel):
    blob_url: str
    media_type: str = "application/octet-stream"
    size_bytes: int = Field(default=0, ge=0)
    encrypted_file_key: str
    nonce: str
    sha256: str = ""


class AttachmentManifestRequest(BaseModel):
    message_id: str
    attachments: list[AttachmentManifestItem]


@router.post("/chat/devices", status_code=status.HTTP_201_CREATED)
async def register_chat_device(
    payload: ChatDeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(select(ChatDevice).where(ChatDevice.device_id == payload.device_id))
    ).scalars().first()
    if existing:
        existing.device_label = payload.device_label
        existing.identity_key_public = payload.identity_key_public
        existing.signed_prekey_public = payload.signed_prekey_public
        existing.signed_prekey_signature = payload.signed_prekey_signature
        existing.is_active = True
        existing.revoked_at = None
        device = existing
    else:
        device = ChatDevice(user_id=current_user.id, **payload.model_dump())
        db.add(device)
        await db.flush()
    db.add(
        ChatSignedPreKey(
            device_id=device.id,
            key_id=1,
            public_key=payload.signed_prekey_public,
            signature=payload.signed_prekey_signature,
        )
    )
    await db.commit()
    return {"device_id": payload.device_id}


@router.post("/chat/prekeys/signed")
async def upload_signed_prekey(
    payload: SignedPreKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    device_id: str | None = None,
):
    if not device_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="device_id query param required")
    device = await get_active_device_or_404(device_id, current_user.id, db)
    db.add(ChatSignedPreKey(device_id=device.id, key_id=payload.key_id, public_key=payload.public_key, signature=payload.signature))
    await db.commit()
    return {"success": True}


@router.post("/chat/prekeys/one-time")
async def upload_one_time_prekeys(
    payload: OneTimePreKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    device_id: str | None = None,
):
    if not device_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="device_id query param required")
    device = await get_active_device_or_404(device_id, current_user.id, db)
    for key in payload.keys:
        db.add(ChatOneTimePreKey(device_id=device.id, key_id=int(key["key_id"]), public_key=str(key["public_key"])))
    await db.commit()
    return {"success": True, "count": len(payload.keys)}


@router.get("/chat/prekeys/{user_id}")
async def fetch_prekey_bundle(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bundle = await get_prekey_bundle_for_user(decode_id_or_404(user_id), db)
    await db.commit()
    return bundle


@router.post("/chat/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await db.get(Order, decode_id_or_404(payload.order_id))
    vendor = await db.get(Vendor, decode_id_or_404(payload.vendor_id))
    if order is None or vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order or vendor not found")
    if current_user.id not in {order.user_id, vendor.owner_user_id} and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to create conversation")
    conversation = await create_order_conversation(order, vendor, current_user.id, db)
    await db.commit()
    return {"conversation_id": encode_id(conversation.id or 0)}


@router.get("/chat/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    participants = (
        await db.execute(select(ChatParticipant).where(ChatParticipant.user_id == current_user.id))
    ).scalars().all()
    items = []
    for participant in participants:
        conversation = await db.get(ChatConversation, participant.conversation_id)
        if conversation:
            items.append(
                {
                    "id": encode_id(conversation.id or 0),
                    "conversation_type": conversation.conversation_type.value,
                    "order_id": encode_id(conversation.order_id) if conversation.order_id else None,
                    "vendor_id": encode_id(conversation.vendor_id) if conversation.vendor_id else None,
                    "created_at": conversation.created_at.isoformat(),
                    "last_read_message_id": encode_id(participant.last_read_message_id) if participant.last_read_message_id else None,
                }
            )
    return {"items": items, "total": len(items)}


@router.post("/chat/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: str,
    payload: MessageSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_conversation_or_404(decode_id_or_404(conversation_id), db)
    device = await get_active_device_or_404(payload.device_id, current_user.id, db)
    envelope = await send_encrypted_message(
        conversation_id=conversation.id,
        sender_user_id=current_user.id,
        sender_device=device,
        ciphertext=payload.ciphertext,
        header=payload.header,
        attachments=payload.attachments,
        db=db,
    )
    await db.commit()
    return {"message_id": encode_id(envelope.id or 0)}


@router.get("/chat/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    messages = await list_conversation_messages(decode_id_or_404(conversation_id), current_user.id, db)
    return {
        "items": [
            {
                "id": encode_id(message.id or 0),
                "sender_user_id": encode_id(message.sender_user_id),
                "sender_device_id": encode_id(message.sender_device_id),
                "ciphertext": message.ciphertext,
                "header": json.loads(message.header_json or "{}"),
                "attachments": json.loads(message.attachment_manifest_json or "[]"),
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ],
        "total": len(messages),
    }


@router.post("/chat/attachments", status_code=status.HTTP_201_CREATED)
async def create_attachment_manifest(
    payload: AttachmentManifestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await db.get(ChatMessageEnvelope, decode_id_or_404(payload.message_id))
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    participant = (
        await db.execute(
            select(ChatParticipant).where(
                ChatParticipant.conversation_id == message.conversation_id,
                ChatParticipant.user_id == current_user.id,
            )
        )
    ).scalars().first()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
    manifest = json.loads(message.attachment_manifest_json or "[]")
    for item in payload.attachments:
        item_payload = item.model_dump()
        manifest.append(item_payload)
        db.add(ChatAttachment(message_id=message.id, **item_payload))
    message.attachment_manifest_json = json.dumps(manifest)
    await db.commit()
    return {"message_id": encode_id(message.id or 0), "attachment_count": len(manifest)}


@router.get("/chat/attachments/{message_id}")
async def list_message_attachments(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await db.get(ChatMessageEnvelope, decode_id_or_404(message_id))
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    participant = (
        await db.execute(
            select(ChatParticipant).where(
                ChatParticipant.conversation_id == message.conversation_id,
                ChatParticipant.user_id == current_user.id,
            )
        )
    ).scalars().first()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
    attachments = (
        await db.execute(select(ChatAttachment).where(ChatAttachment.message_id == message.id).order_by(ChatAttachment.id.asc()))
    ).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(attachment.id or 0),
                "message_id": encode_id(attachment.message_id),
                "blob_url": attachment.blob_url,
                "media_type": attachment.media_type,
                "size_bytes": attachment.size_bytes,
                "encrypted_file_key": attachment.encrypted_file_key,
                "nonce": attachment.nonce,
                "sha256": attachment.sha256,
            }
            for attachment in attachments
        ],
        "total": len(attachments),
    }


@router.post("/chat/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: str,
    payload: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    participant = (
        await db.execute(
            select(ChatParticipant).where(
                ChatParticipant.conversation_id == decode_id_or_404(conversation_id),
                ChatParticipant.user_id == current_user.id,
            )
        )
    ).scalars().first()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
    message_id = decode_id_or_404(payload.message_id)
    participant.last_read_message_id = message_id
    db.add(
        ChatReadReceipt(
            conversation_id=participant.conversation_id,
            message_id=message_id,
            user_id=current_user.id,
            device_id=(await get_active_device_or_404(payload.device_id, current_user.id, db)).id if payload.device_id else None,
        )
    )
    await db.commit()
    return {"success": True}


@router.put("/chat/backup")
async def upload_key_backup(
    payload: BackupBlobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    backup = await save_key_backup(current_user.id, payload.backup_blob, payload.salt, payload.metadata, db)
    await db.commit()
    return {"backup_id": encode_id(backup.id or 0)}


@router.get("/chat/backup")
async def get_key_backup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    backup = (await db.execute(select(ChatKeyBackup).where(ChatKeyBackup.user_id == current_user.id))).scalars().first()
    if backup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No key backup found")
    return {
        "backup_blob": backup.backup_blob,
        "salt": backup.salt,
        "metadata": json.loads(backup.metadata_json or "{}"),
        "updated_at": backup.updated_at.isoformat(),
    }


@router.post("/chat/reports", status_code=status.HTTP_201_CREATED)
async def create_chat_report(
    conversation_id: str,
    payload: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = await get_conversation_or_404(decode_id_or_404(conversation_id), db)
    report = ChatReport(
        conversation_id=conversation.id,
        reported_by_user_id=current_user.id,
        reason=payload.reason,
        metadata_json=json.dumps(payload.metadata),
    )
    db.add(report)
    await db.commit()
    return {"report_id": encode_id(report.id or 0)}


@router.post("/chat/devices/{device_id}/revoke")
async def revoke_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    device = await get_active_device_or_404(device_id, current_user.id, db)
    device.is_active = False
    device.revoked_at = utc_now()
    await db.commit()
    return {"success": True}


@router.get("/admin/chat/reports")
async def list_chat_reports(
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    reports = (await db.execute(select(ChatReport).order_by(ChatReport.created_at.desc()))).scalars().all()
    return {
        "items": [
            {
                "id": encode_id(report.id or 0),
                "conversation_id": encode_id(report.conversation_id),
                "reported_by_user_id": encode_id(report.reported_by_user_id),
                "reason": report.reason,
                "metadata": json.loads(report.metadata_json or "{}"),
                "created_at": report.created_at.isoformat(),
            }
            for report in reports
        ],
        "total": len(reports),
    }

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from src.apps.core.time import utc_now


class ChatConversationType(str, Enum):
    ORDER = "order"
    SUPPORT = "support"
    GENERAL = "general"


class ChatParticipantRole(str, Enum):
    CUSTOMER = "customer"
    VENDOR = "vendor"
    SUPPORT = "support"


class ChatDevice(SQLModel, table=True):
    __tablename__ = "chat_devices"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    device_id: str = Field(max_length=120, unique=True, index=True)
    device_label: str = Field(default="", max_length=120)
    identity_key_public: str = Field(max_length=4096)
    signed_prekey_public: str = Field(max_length=4096)
    signed_prekey_signature: str = Field(max_length=4096)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    revoked_at: Optional[datetime] = Field(default=None)


class ChatSignedPreKey(SQLModel, table=True):
    __tablename__ = "chat_signed_prekeys"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="chat_devices.id", index=True)
    key_id: int = Field(index=True)
    public_key: str = Field(max_length=4096)
    signature: str = Field(max_length=4096)
    created_at: datetime = Field(default_factory=utc_now)


class ChatOneTimePreKey(SQLModel, table=True):
    __tablename__ = "chat_one_time_prekeys"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="chat_devices.id", index=True)
    key_id: int = Field(index=True)
    public_key: str = Field(max_length=4096)
    is_consumed: bool = Field(default=False)
    consumed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class ChatConversation(SQLModel, table=True):
    __tablename__ = "chat_conversations"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_type: ChatConversationType = Field(default=ChatConversationType.ORDER)
    order_id: Optional[int] = Field(default=None, foreign_key="orders.id", index=True)
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendors.id", index=True)
    support_ticket_id: Optional[int] = Field(default=None, foreign_key="support_tickets.id", index=True)
    created_by_user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    closed_at: Optional[datetime] = Field(default=None)


class ChatParticipant(SQLModel, table=True):
    __tablename__ = "chat_participants"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="chat_conversations.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: ChatParticipantRole = Field(default=ChatParticipantRole.CUSTOMER)
    joined_at: datetime = Field(default_factory=utc_now)
    last_read_message_id: Optional[int] = Field(default=None, foreign_key="chat_message_envelopes.id")


class ChatMessageEnvelope(SQLModel, table=True):
    __tablename__ = "chat_message_envelopes"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="chat_conversations.id", index=True)
    sender_user_id: int = Field(foreign_key="user.id", index=True)
    sender_device_id: int = Field(foreign_key="chat_devices.id", index=True)
    message_type: str = Field(default="ciphertext", max_length=50)
    ciphertext: str = Field(max_length=32768)
    header_json: str = Field(default="{}")
    attachment_manifest_json: str = Field(default="[]")
    created_at: datetime = Field(default_factory=utc_now)


class ChatAttachment(SQLModel, table=True):
    __tablename__ = "chat_attachments"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="chat_message_envelopes.id", index=True)
    blob_url: str = Field(max_length=1000)
    media_type: str = Field(default="application/octet-stream", max_length=120)
    size_bytes: int = Field(default=0, ge=0)
    encrypted_file_key: str = Field(max_length=4096)
    nonce: str = Field(max_length=1024)
    sha256: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=utc_now)


class ChatReadReceipt(SQLModel, table=True):
    __tablename__ = "chat_read_receipts"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="chat_conversations.id", index=True)
    message_id: int = Field(foreign_key="chat_message_envelopes.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    device_id: Optional[int] = Field(default=None, foreign_key="chat_devices.id", index=True)
    read_at: datetime = Field(default_factory=utc_now)


class ChatKeyBackup(SQLModel, table=True):
    __tablename__ = "chat_key_backups"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    backup_blob: str = Field(max_length=32768)
    backup_version: str = Field(default="v1", max_length=20)
    salt: str = Field(max_length=1024)
    metadata_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatReport(SQLModel, table=True):
    __tablename__ = "chat_reports"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="chat_conversations.id", index=True)
    reported_by_user_id: int = Field(foreign_key="user.id", index=True)
    reason: str = Field(max_length=255)
    metadata_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)

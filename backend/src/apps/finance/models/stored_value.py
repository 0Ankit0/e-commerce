from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class WalletLedgerType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    GIFT_CARD = "gift_card"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class WalletLedger(SQLModel, table=True):
    __tablename__ = "wallet_ledger"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    entry_type: WalletLedgerType = Field(default=WalletLedgerType.CREDIT)
    amount: int = Field(description="Amount in the smallest currency unit")
    balance_after: int = Field(description="Balance after this entry in the smallest currency unit")
    reference_type: str = Field(default="", max_length=50)
    reference_id: Optional[int] = Field(default=None, index=True)
    notes: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=datetime.now)


class GiftCardStatus(str, Enum):
    ACTIVE = "active"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    DISABLED = "disabled"


class GiftCard(SQLModel, table=True):
    __tablename__ = "gift_cards"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=80, unique=True, index=True)
    initial_amount: int = Field(description="Initial amount in the smallest currency unit")
    remaining_amount: int = Field(description="Remaining amount in the smallest currency unit")
    currency: str = Field(default="NPR", max_length=3)
    status: GiftCardStatus = Field(default=GiftCardStatus.ACTIVE)
    expires_at: Optional[datetime] = Field(default=None)
    redeemed_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    redeemed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)

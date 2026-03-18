from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.finance.models.payment import PaymentProvider, PaymentStatus, PaymentTransaction
from src.apps.finance.models.stored_value import GiftCard, GiftCardStatus, WalletLedger, WalletLedgerType


async def get_wallet_balance(user_id: int, db: AsyncSession) -> int:
    latest_entry = (
        await db.execute(
            select(WalletLedger).where(WalletLedger.user_id == user_id).order_by(WalletLedger.id.desc())
        )
    ).scalars().first()
    return latest_entry.balance_after if latest_entry else 0


async def create_wallet_entry(
    *,
    user_id: int,
    amount: int,
    entry_type: WalletLedgerType,
    reference_type: str,
    reference_id: int | None,
    notes: str,
    db: AsyncSession,
) -> WalletLedger:
    current_balance = await get_wallet_balance(user_id, db)
    new_balance = current_balance + amount if entry_type != WalletLedgerType.DEBIT else current_balance - amount
    if new_balance < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient wallet balance")
    entry = WalletLedger(
        user_id=user_id,
        amount=amount,
        entry_type=entry_type,
        balance_after=new_balance,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
    )
    db.add(entry)
    await db.flush()
    return entry


async def redeem_gift_card(code: str, user_id: int, db: AsyncSession) -> GiftCard:
    gift_card = (
        await db.execute(select(GiftCard).where(GiftCard.code == code.upper()))
    ).scalars().first()
    if gift_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift card not found")
    if gift_card.status != GiftCardStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift card is not active")
    if gift_card.expires_at and gift_card.expires_at < datetime.now():
        gift_card.status = GiftCardStatus.EXPIRED
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift card has expired")
    amount = gift_card.remaining_amount
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift card has no remaining balance")
    await create_wallet_entry(
        user_id=user_id,
        amount=amount,
        entry_type=WalletLedgerType.GIFT_CARD,
        reference_type="gift_card",
        reference_id=gift_card.id,
        notes=f"Redeemed gift card {gift_card.code}",
        db=db,
    )
    gift_card.remaining_amount = 0
    gift_card.status = GiftCardStatus.REDEEMED
    gift_card.redeemed_by_user_id = user_id
    gift_card.redeemed_at = datetime.now()
    return gift_card


async def create_wallet_payment_transaction(
    *,
    user_id: int,
    amount: int,
    purchase_order_id: str,
    purchase_order_name: str,
    return_url: str,
    website_url: str,
    idempotency_key: str | None,
    db: AsyncSession,
) -> PaymentTransaction:
    tx = PaymentTransaction(
        provider=PaymentProvider.WALLET,
        amount=amount,
        status=PaymentStatus.COMPLETED,
        purchase_order_id=purchase_order_id,
        purchase_order_name=purchase_order_name,
        return_url=return_url,
        website_url=website_url,
        user_id=user_id,
        captured_amount=amount,
        idempotency_key=idempotency_key,
    )
    db.add(tx)
    await db.flush()
    return tx

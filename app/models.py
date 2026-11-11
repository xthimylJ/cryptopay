"""
Database models (tables).

Three tables:
  merchants       - businesses that use CryptoPay to accept payments
  payments        - one payment request ("invoice") created by a merchant
  webhook_events  - log of notifications we sent to merchants' servers
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaymentStatus(str, enum.Enum):
    """
    Lifecycle of a payment (see the state machine diagram):

    PENDING     -> created, waiting for the customer to pay
    CONFIRMING  -> customer sent a transaction, waiting for the blockchain
    PAID        -> transaction verified and confirmed (final)
    FAILED      -> transaction was invalid (wrong amount/address, reverted)
    EXPIRED     -> customer did not pay in time (final)
    CANCELED    -> merchant canceled the payment (final)
    """
    PENDING = "pending"
    CONFIRMING = "confirming"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELED = "canceled"


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Ethereum address where this merchant receives money (0x + 40 hex chars).
    wallet_address: Mapped[str] = mapped_column(String(42))
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # We store only a SHA-256 hash of the API key, never the key itself.
    # Like passwords: if the DB leaks, the keys are still safe.
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # First characters of the key, so the merchant can recognise it in the UI.
    api_key_prefix: Mapped[str] = mapped_column(String(20))
    # Secret used to sign webhooks (HMAC). Needed in plain form to sign.
    webhook_secret: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payments: Mapped[list["Payment"]] = relationship(back_populates="merchant")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), index=True)
    # Amount in wei (1 ETH = 10^18 wei), stored as a digit string.
    # Why not float? Floats round (0.1 + 0.2 != 0.3) - unacceptable for money.
    # Why not a normal integer? Large wei values overflow 64-bit integers.
    amount_wei: Mapped[str] = mapped_column(String(78))
    currency: Mapped[str] = mapped_column(String(10), default="ETH")
    network: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # The merchant's own order number, so they can match our payment to it.
    order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Address the customer must pay to (copied from the merchant at creation).
    to_address: Mapped[str] = mapped_column(String(42))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=20), default=PaymentStatus.PENDING
    )
    # UNIQUE: one blockchain transaction can pay for only one payment.
    # This prevents a "replay" attack - reusing one old transaction twice.
    tx_hash: Mapped[str | None] = mapped_column(String(66), unique=True, nullable=True)
    payer_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    success_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    merchant: Mapped[Merchant] = relationship(back_populates="payments")
    webhook_events: Mapped[list["WebhookEvent"]] = relationship(back_populates="payment")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))   # e.g. "payment.paid"
    url: Mapped[str] = mapped_column(String(500))
    payload: Mapped[str] = mapped_column(Text)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    payment: Mapped[Payment] = relationship(back_populates="webhook_events")

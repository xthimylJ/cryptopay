"""
Repositories - the only place that talks to the database.

Repository pattern: services ask "give me payment X" or "save this", and do
not care whether the data lives in SQLite, PostgreSQL or somewhere else.
(Single Responsibility: data access is separated from business rules.)
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Merchant, Payment, WebhookEvent


class MerchantRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, merchant: Merchant) -> Merchant:
        self.db.add(merchant)
        self.db.commit()
        self.db.refresh(merchant)
        return merchant

    def save(self, merchant: Merchant) -> Merchant:
        self.db.commit()
        self.db.refresh(merchant)
        return merchant

    def get_by_email(self, email: str) -> Merchant | None:
        return self.db.scalar(select(Merchant).where(Merchant.email == email))

    def get_by_api_key_hash(self, key_hash: str) -> Merchant | None:
        return self.db.scalar(select(Merchant).where(Merchant.api_key_hash == key_hash))


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def save(self, payment: Payment) -> Payment:
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get(self, payment_id: str) -> Payment | None:
        return self.db.get(Payment, payment_id)

    def get_by_tx_hash(self, tx_hash: str) -> Payment | None:
        return self.db.scalar(select(Payment).where(Payment.tx_hash == tx_hash))

    def list_for_merchant(self, merchant_id: str, limit: int = 50) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.merchant_id == merchant_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))


class WebhookEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, event: WebhookEvent) -> WebhookEvent:
        self.db.add(event)
        self.db.commit()
        return event

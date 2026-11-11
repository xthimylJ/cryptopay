"""
PaymentService - the core business logic of CryptoPay.

Notice the constructor: the service RECEIVES its dependencies
(repository, blockchain gateway, webhook notifier) instead of creating them.
This is Dependency Injection. Because of it:
  - in production we pass SepoliaGateway,
  - in tests and demos we pass MockGateway,
and this file does not change. (Dependency Inversion + Open/Closed.)
"""
from datetime import datetime, timedelta, timezone

from app.blockchain.base import BlockchainGateway, TxStatus
from app.config import settings
from app.models import Merchant, Payment, PaymentStatus
from app.repositories import PaymentRepository
from app.schemas import PaymentCreate
from app.services.errors import ConflictError, InvalidStateError, NotFoundError
from app.services.webhook_service import WebhookNotifier
from app.utils import as_utc, eth_to_wei, new_id

FINAL_STATUSES = {PaymentStatus.PAID, PaymentStatus.FAILED,
                  PaymentStatus.EXPIRED, PaymentStatus.CANCELED}


class PaymentService:
    def __init__(self, payments: PaymentRepository, gateway: BlockchainGateway,
                 notifier: WebhookNotifier):
        self.payments = payments
        self.gateway = gateway
        self.notifier = notifier

    # ---------- Merchant side ----------

    def create_payment(self, merchant: Merchant, data: PaymentCreate) -> Payment:
        try:
            amount_wei = eth_to_wei(data.amount)
        except ValueError as exc:
            raise InvalidStateError(str(exc)) from exc

        now = datetime.now(timezone.utc)
        payment = Payment(
            id=new_id("pay"),
            merchant_id=merchant.id,
            amount_wei=str(amount_wei),
            currency="ETH",
            network=self.gateway.network_name,
            description=data.description,
            order_id=data.order_id,
            # Copy the address now: if the merchant later changes their
            # wallet, already-issued payments still point to the old one.
            to_address=merchant.wallet_address,
            status=PaymentStatus.PENDING,
            success_url=data.success_url,
            created_at=now,
            expires_at=now + timedelta(minutes=settings.PAYMENT_TTL_MINUTES),
        )
        return self.payments.add(payment)

    def get_for_merchant(self, merchant: Merchant, payment_id: str) -> Payment:
        payment = self.payments.get(payment_id)
        # A merchant must never see another merchant's payment -> same 404.
        if payment is None or payment.merchant_id != merchant.id:
            raise NotFoundError("Payment not found")
        return self._expire_if_needed(payment)

    def list_for_merchant(self, merchant: Merchant) -> list[Payment]:
        return [self._expire_if_needed(p) for p in self.payments.list_for_merchant(merchant.id)]

    def cancel(self, merchant: Merchant, payment_id: str) -> Payment:
        payment = self.get_for_merchant(merchant, payment_id)
        if payment.status != PaymentStatus.PENDING:
            raise InvalidStateError(f"Cannot cancel a payment in status '{payment.status.value}'")
        payment.status = PaymentStatus.CANCELED
        self.payments.save(payment)
        self.notifier.notify(payment, "payment.canceled")
        return payment

    # ---------- Customer (checkout) side ----------

    def get_for_checkout(self, payment_id: str) -> Payment:
        payment = self.payments.get(payment_id)
        if payment is None:
            raise NotFoundError("Payment not found")
        return self._expire_if_needed(payment)

    def submit_transaction(self, payment_id: str, tx_hash: str) -> Payment:
        """Customer's wallet sent a transaction - attach it and verify it."""
        payment = self.get_for_checkout(payment_id)

        if payment.status != PaymentStatus.PENDING:
            raise InvalidStateError(
                f"Payment is '{payment.status.value}', it cannot accept a transaction")

        existing = self.payments.get_by_tx_hash(tx_hash)
        if existing is not None:
            raise ConflictError("This transaction was already used for another payment")

        payment.tx_hash = tx_hash
        payment.status = PaymentStatus.CONFIRMING
        self.payments.save(payment)
        return self._verify(payment)

    def refresh(self, payment_id: str) -> Payment:
        """Called repeatedly by the checkout page while waiting for the chain."""
        payment = self.get_for_checkout(payment_id)
        if payment.status == PaymentStatus.CONFIRMING:
            payment = self._verify(payment)
        return payment

    # ---------- Internal steps ----------

    def _verify(self, payment: Payment) -> Payment:
        result = self.gateway.verify_transaction(
            payment.tx_hash, payment.to_address, int(payment.amount_wei))

        if result.payer_address:
            payment.payer_address = result.payer_address

        if result.status == TxStatus.CONFIRMED:
            payment.status = PaymentStatus.PAID
            payment.paid_at = datetime.now(timezone.utc)
            payment.failure_reason = None
            self.payments.save(payment)
            self.notifier.notify(payment, "payment.paid")
        elif result.status == TxStatus.FAILED:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = result.reason
            self.payments.save(payment)
            self.notifier.notify(payment, "payment.failed")
        else:
            # Still pending: remember why, so the page can show progress.
            payment.failure_reason = None
            self.payments.save(payment)
        return payment

    def _expire_if_needed(self, payment: Payment) -> Payment:
        """
        Lazy expiration: instead of a background job, we check the deadline
        whenever the payment is read. Simple and needs no extra process.
        """
        if (payment.status == PaymentStatus.PENDING
                and datetime.now(timezone.utc) > as_utc(payment.expires_at)):
            payment.status = PaymentStatus.EXPIRED
            self.payments.save(payment)
            self.notifier.notify(payment, "payment.expired")
        return payment

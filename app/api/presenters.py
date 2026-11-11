"""Convert DB objects into API responses (adds computed fields like checkout_url)."""
from app.blockchain.base import BlockchainGateway
from app.config import settings
from app.models import Payment
from app.schemas import CheckoutInfo, PaymentOut
from app.utils import as_utc, wei_to_eth


def checkout_url(payment: Payment) -> str:
    return f"{settings.BASE_URL}/pay/{payment.id}"


def payment_out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id, status=p.status, amount=wei_to_eth(p.amount_wei), amount_wei=p.amount_wei,
        currency=p.currency, network=p.network, description=p.description,
        order_id=p.order_id, to_address=p.to_address, tx_hash=p.tx_hash,
        payer_address=p.payer_address, failure_reason=p.failure_reason,
        checkout_url=checkout_url(p), created_at=as_utc(p.created_at),
        expires_at=as_utc(p.expires_at), paid_at=as_utc(p.paid_at),
    )


def checkout_info(p: Payment, gateway: BlockchainGateway) -> CheckoutInfo:
    return CheckoutInfo(
        id=p.id, status=p.status, merchant_name=p.merchant.name,
        amount=wei_to_eth(p.amount_wei), amount_wei=p.amount_wei, currency=p.currency,
        network=p.network, chain_id=gateway.chain_id, to_address=p.to_address,
        description=p.description, tx_hash=p.tx_hash, failure_reason=p.failure_reason,
        expires_at=as_utc(p.expires_at), success_url=p.success_url,
        mode=settings.BLOCKCHAIN_MODE,
    )

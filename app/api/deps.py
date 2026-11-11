"""
Dependency wiring (the "composition root").

FastAPI's Depends() builds objects for every request and passes them into
route functions. This is the ONLY place where concrete classes are glued
together; routes and services just receive what they need.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.blockchain.base import BlockchainGateway
from app.blockchain.factory import get_blockchain_gateway
from app.database import get_db
from app.models import Merchant
from app.repositories import MerchantRepository, PaymentRepository, WebhookEventRepository
from app.services.merchant_service import MerchantService
from app.services.payment_service import PaymentService
from app.services.webhook_service import HttpWebhookNotifier

bearer = HTTPBearer(auto_error=False, description="Your secret API key: sk_test_...")


def get_merchant_service(db: Session = Depends(get_db)) -> MerchantService:
    return MerchantService(MerchantRepository(db))


def get_payment_service(
    db: Session = Depends(get_db),
    gateway: BlockchainGateway = Depends(get_blockchain_gateway),
) -> PaymentService:
    notifier = HttpWebhookNotifier(WebhookEventRepository(db))
    return PaymentService(PaymentRepository(db), gateway, notifier)


def get_current_merchant(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    merchants: MerchantService = Depends(get_merchant_service),
) -> Merchant:
    """Reads 'Authorization: Bearer sk_test_...' and finds the merchant."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")
    merchant = merchants.authenticate(credentials.credentials)
    if merchant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return merchant

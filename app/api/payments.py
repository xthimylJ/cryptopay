"""
Payment endpoints for merchants (server-to-server, need an API key).

Typical integration, exactly like Stripe Checkout:
  1. The shop's backend calls POST /v1/payments with the order amount.
  2. It redirects the customer to the returned `checkout_url`.
  3. CryptoPay sends a webhook to the shop when the payment is PAID.
"""
from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_merchant, get_payment_service
from app.api.presenters import payment_out
from app.models import Merchant
from app.schemas import PaymentCreate, PaymentOut
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/v1/payments", tags=["Payments"])


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED,
             summary="Create a payment and get a checkout link")
def create_payment(data: PaymentCreate,
                   merchant: Merchant = Depends(get_current_merchant),
                   service: PaymentService = Depends(get_payment_service)):
    return payment_out(service.create_payment(merchant, data))


@router.get("", response_model=list[PaymentOut], summary="List my payments")
def list_payments(merchant: Merchant = Depends(get_current_merchant),
                  service: PaymentService = Depends(get_payment_service)):
    return [payment_out(p) for p in service.list_for_merchant(merchant)]


@router.get("/{payment_id}", response_model=PaymentOut, summary="Get one payment")
def get_payment(payment_id: str,
                merchant: Merchant = Depends(get_current_merchant),
                service: PaymentService = Depends(get_payment_service)):
    return payment_out(service.get_for_merchant(merchant, payment_id))


@router.post("/{payment_id}/cancel", response_model=PaymentOut, summary="Cancel a pending payment")
def cancel_payment(payment_id: str,
                   merchant: Merchant = Depends(get_current_merchant),
                   service: PaymentService = Depends(get_payment_service)):
    return payment_out(service.cancel(merchant, payment_id))

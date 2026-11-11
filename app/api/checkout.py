"""
Public checkout endpoints, used by the customer's browser (no API key).

The customer only knows the payment id from the link, so these endpoints
return only public information - never keys or other merchants' data.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_payment_service
from app.api.presenters import checkout_info
from app.schemas import CheckoutInfo, SubmitTransaction
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/checkout", tags=["Checkout (customer)"])


@router.get("/{payment_id}", response_model=CheckoutInfo, summary="Payment info for the checkout page")
def get_checkout(payment_id: str, service: PaymentService = Depends(get_payment_service)):
    return checkout_info(service.get_for_checkout(payment_id), service.gateway)


@router.post("/{payment_id}/transaction", response_model=CheckoutInfo,
             summary="Attach the customer's blockchain transaction")
def submit_transaction(payment_id: str, data: SubmitTransaction,
                       service: PaymentService = Depends(get_payment_service)):
    return checkout_info(service.submit_transaction(payment_id, data.tx_hash), service.gateway)


@router.post("/{payment_id}/refresh", response_model=CheckoutInfo,
             summary="Re-check the transaction on the blockchain")
def refresh(payment_id: str, service: PaymentService = Depends(get_payment_service)):
    return checkout_info(service.refresh(payment_id), service.gateway)

"""Merchant endpoints: registration and account settings."""
from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_merchant, get_merchant_service
from app.models import Merchant
from app.schemas import MerchantCreate, MerchantCreated, MerchantOut, MerchantUpdate
from app.services.merchant_service import MerchantService

router = APIRouter(prefix="/v1/merchants", tags=["Merchants"])


@router.post("", response_model=MerchantCreated, status_code=status.HTTP_201_CREATED,
             summary="Register a business and get API keys")
def register_merchant(data: MerchantCreate,
                      service: MerchantService = Depends(get_merchant_service)):
    merchant, api_key = service.register(data)
    return MerchantCreated(**MerchantOut.model_validate(merchant).model_dump(),
                           api_key=api_key, webhook_secret=merchant.webhook_secret)


@router.get("/me", response_model=MerchantOut, summary="Get my merchant account")
def get_me(merchant: Merchant = Depends(get_current_merchant)):
    return merchant


@router.patch("/me", response_model=MerchantOut, summary="Update wallet or webhook URL")
def update_me(data: MerchantUpdate,
              merchant: Merchant = Depends(get_current_merchant),
              service: MerchantService = Depends(get_merchant_service)):
    return service.update(merchant, data)

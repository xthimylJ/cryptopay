"""
Pydantic schemas = the shape of data that enters and leaves the API.

They are separate from the DB models on purpose (Single Responsibility):
models describe how data is STORED, schemas describe how it is SENT.
For example, the API key hash is in the model but never in a schema,
so it can never leak through the API by accident.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import PaymentStatus
from app.utils import is_eth_address, is_tx_hash


# ---------- Merchants ----------

class MerchantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120, examples=["Coffee Shop"])
    email: EmailStr = Field(examples=["owner@coffee.kg"])
    wallet_address: str = Field(examples=["0x1111111111111111111111111111111111111111"])
    webhook_url: str | None = Field(default=None, examples=["https://webhook.site/your-id"])

    @field_validator("wallet_address")
    @classmethod
    def check_address(cls, v: str) -> str:
        if not is_eth_address(v):
            raise ValueError("wallet_address must be 0x followed by 40 hex characters")
        return v

    @field_validator("webhook_url")
    @classmethod
    def check_url(cls, v: str | None) -> str | None:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("webhook_url must start with http:// or https://")
        return v or None


class MerchantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    wallet_address: str | None = None
    webhook_url: str | None = None

    @field_validator("wallet_address")
    @classmethod
    def check_address(cls, v: str | None) -> str | None:
        if v is not None and not is_eth_address(v):
            raise ValueError("wallet_address must be 0x followed by 40 hex characters")
        return v

    @field_validator("webhook_url")
    @classmethod
    def check_url(cls, v: str | None) -> str | None:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("webhook_url must start with http:// or https://")
        return v


class MerchantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    wallet_address: str
    webhook_url: str | None
    api_key_prefix: str
    created_at: datetime


class MerchantCreated(MerchantOut):
    """Returned ONCE at registration - the only time the secrets are shown."""
    api_key: str
    webhook_secret: str


# ---------- Payments ----------

class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, le=1000, examples=["0.001"],
                            description="Amount in ETH")
    description: str | None = Field(default=None, max_length=500, examples=["Latte x2"])
    order_id: str | None = Field(default=None, max_length=100, examples=["ORDER-1024"])
    success_url: str | None = Field(default=None, examples=["https://coffee.kg/thanks"])


class PaymentOut(BaseModel):
    id: str
    status: PaymentStatus
    amount: str            # in ETH, as a string to avoid float rounding
    amount_wei: str
    currency: str
    network: str
    description: str | None
    order_id: str | None
    to_address: str
    tx_hash: str | None
    payer_address: str | None
    failure_reason: str | None
    checkout_url: str
    created_at: datetime
    expires_at: datetime
    paid_at: datetime | None


class CheckoutInfo(BaseModel):
    """Public data shown to the customer on the checkout page (no secrets)."""
    id: str
    status: PaymentStatus
    merchant_name: str
    amount: str
    amount_wei: str
    currency: str
    network: str
    chain_id: int
    to_address: str
    description: str | None
    tx_hash: str | None
    failure_reason: str | None
    expires_at: datetime
    success_url: str | None
    mode: str              # "sepolia" or "mock"


class SubmitTransaction(BaseModel):
    tx_hash: str = Field(examples=["0x" + "ab" * 32])

    @field_validator("tx_hash")
    @classmethod
    def check_hash(cls, v: str) -> str:
        if not is_tx_hash(v):
            raise ValueError("tx_hash must be 0x followed by 64 hex characters")
        return v.lower()

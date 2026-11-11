"""Merchant use cases: register, authenticate, update settings."""
from app.models import Merchant
from app.repositories import MerchantRepository
from app.schemas import MerchantCreate, MerchantUpdate
from app.security import generate_api_key, generate_webhook_secret, hash_api_key
from app.services.errors import ConflictError
from app.utils import new_id


class MerchantService:
    def __init__(self, merchants: MerchantRepository):
        self.merchants = merchants

    def register(self, data: MerchantCreate) -> tuple[Merchant, str]:
        """Returns the new merchant AND the plain API key (shown only once)."""
        if self.merchants.get_by_email(data.email):
            raise ConflictError("A merchant with this email already exists")

        api_key = generate_api_key()
        merchant = Merchant(
            id=new_id("mer"),
            name=data.name,
            email=data.email,
            wallet_address=data.wallet_address,
            webhook_url=data.webhook_url,
            api_key_hash=hash_api_key(api_key),
            api_key_prefix=api_key[:12],
            webhook_secret=generate_webhook_secret(),
        )
        return self.merchants.add(merchant), api_key

    def authenticate(self, api_key: str) -> Merchant | None:
        return self.merchants.get_by_api_key_hash(hash_api_key(api_key))

    def update(self, merchant: Merchant, data: MerchantUpdate) -> Merchant:
        # exclude_unset: change only the fields the client actually sent.
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(merchant, field, value)
        return self.merchants.save(merchant)

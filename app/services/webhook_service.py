"""
Webhooks: how CryptoPay tells the merchant's server "this order is paid".

Stripe-style flow: the merchant gives us a URL. When a payment changes
status, we POST a signed JSON message to that URL. The merchant's server
then marks the order as paid in their own system.
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from app.models import Payment, WebhookEvent
from app.repositories import WebhookEventRepository
from app.security import sign_payload
from app.utils import wei_to_eth

log = logging.getLogger("cryptopay.webhooks")


class WebhookNotifier(ABC):
    """Abstraction (Interface Segregation + Dependency Inversion)."""

    @abstractmethod
    def notify(self, payment: Payment, event_type: str) -> None: ...


def build_event_payload(payment: Payment, event_type: str) -> dict:
    return {
        "type": event_type,
        "created": datetime.now(timezone.utc).isoformat(),
        "data": {
            "id": payment.id,
            "status": payment.status.value,
            "amount": wei_to_eth(payment.amount_wei),
            "currency": payment.currency,
            "order_id": payment.order_id,
            "tx_hash": payment.tx_hash,
            "payer_address": payment.payer_address,
        },
    }


class HttpWebhookNotifier(WebhookNotifier):
    def __init__(self, events: WebhookEventRepository, http_client: httpx.Client | None = None):
        self.events = events
        self.http = http_client or httpx.Client(timeout=5)

    def notify(self, payment: Payment, event_type: str) -> None:
        url = payment.merchant.webhook_url
        if not url:
            return  # merchant did not configure webhooks

        body = json.dumps(build_event_payload(payment, event_type)).encode()
        signature = sign_payload(body, payment.merchant.webhook_secret)
        headers = {
            "Content-Type": "application/json",
            "X-CryptoPay-Event": event_type,
            "X-CryptoPay-Signature": signature,
        }

        status_code = None
        try:
            response = self.http.post(url, content=body, headers=headers)
            status_code = response.status_code
        except httpx.HTTPError as exc:
            # A broken merchant server must never break our payment flow.
            log.warning("Webhook to %s failed: %s", url, exc)

        # Every attempt is logged in the DB (audit trail).
        self.events.add(WebhookEvent(
            payment_id=payment.id,
            event_type=event_type,
            url=url,
            payload=body.decode(),
            response_status=status_code,
            success=status_code is not None and 200 <= status_code < 300,
        ))

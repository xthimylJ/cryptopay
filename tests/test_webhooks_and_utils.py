"""Webhook signing and money-conversion tests."""
import json

import httpx
import pytest

from app.models import Merchant, Payment, PaymentStatus
from app.security import verify_signature
from app.services.webhook_service import HttpWebhookNotifier
from app.utils import eth_to_wei, wei_to_eth


class FakeEventRepo:
    def __init__(self):
        self.saved = []

    def add(self, event):
        self.saved.append(event)
        return event


def test_webhook_is_signed_and_logged():
    captured = {}

    def handler(request):
        captured["body"] = request.content
        captured["signature"] = request.headers["X-CryptoPay-Signature"]
        return httpx.Response(200)

    merchant = Merchant(id="mer_1", webhook_url="https://shop.kg/hook", webhook_secret="whsec_abc")
    payment = Payment(id="pay_1", merchant=merchant, amount_wei="1000000000000000",
                      currency="ETH", status=PaymentStatus.PAID, order_id="A-1")
    repo = FakeEventRepo()
    notifier = HttpWebhookNotifier(repo, httpx.Client(transport=httpx.MockTransport(handler)))

    notifier.notify(payment, "payment.paid")

    event = json.loads(captured["body"])
    assert event["type"] == "payment.paid" and event["data"]["amount"] == "0.001"
    # The merchant can verify the signature with its secret...
    assert verify_signature(captured["body"], "whsec_abc", captured["signature"])
    # ...and a fake signature or wrong secret is detected.
    assert not verify_signature(captured["body"], "whsec_wrong", captured["signature"])
    assert repo.saved[0].success is True


def test_webhook_failure_does_not_crash():
    def handler(request):
        raise httpx.ConnectError("merchant server down")

    merchant = Merchant(id="mer_1", webhook_url="https://shop.kg/hook", webhook_secret="s")
    payment = Payment(id="pay_1", merchant=merchant, amount_wei="1", currency="ETH",
                      status=PaymentStatus.PAID)
    repo = FakeEventRepo()
    HttpWebhookNotifier(repo, httpx.Client(transport=httpx.MockTransport(handler))).notify(
        payment, "payment.paid")
    assert repo.saved[0].success is False


@pytest.mark.parametrize("eth, wei", [
    ("1", 10**18), ("0.001", 10**15), ("0.000000000000000001", 1), ("12.5", 125 * 10**17),
])
def test_eth_wei_conversion(eth, wei):
    assert eth_to_wei(eth) == wei
    assert wei_to_eth(wei) == eth


def test_too_many_decimals_rejected():
    with pytest.raises(ValueError):
        eth_to_wei("0.0000000000000000001")

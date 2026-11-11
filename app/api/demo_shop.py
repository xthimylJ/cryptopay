"""
A tiny "demo shop" webhook receiver.

In real life the webhook goes to the OTHER business's server. To show the
whole flow on the defense without a second server, this endpoint plays the
role of that business: it receives our webhook and verifies the HMAC
signature exactly as a real merchant would.
"""
import json
from collections import deque
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment
from app.security import verify_signature

router = APIRouter(prefix="/demo", tags=["Demo shop (merchant side)"])

# Kept in memory only - it's a demo, it resets on restart.
received: deque = deque(maxlen=30)


@router.post("/webhook-receiver", summary="Demo merchant server: receive a webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-CryptoPay-Signature", "")
    event = json.loads(body)

    # A real merchant knows its own secret; here we look it up for the demo.
    payment = db.get(Payment, event["data"]["id"])
    valid = payment is not None and verify_signature(body, payment.merchant.webhook_secret, signature)

    received.appendleft({
        "received_at": datetime.now(timezone.utc).isoformat(),
        "merchant_id": payment.merchant_id if payment else None,
        "event": event["type"],
        "payment_id": event["data"]["id"],
        "order_id": event["data"]["order_id"],
        "signature_valid": valid,
    })
    return {"received": True, "signature_valid": valid}


@router.get("/webhook-receiver", summary="Webhooks the demo shop received")
def list_received(merchant_id: str | None = None):
    return [e for e in received if merchant_id is None or e["merchant_id"] == merchant_id]

"""
API keys and webhook signatures.

API key: a long random secret ("sk_test_...") that a merchant's server sends
in every request:  Authorization: Bearer sk_test_...
We store only its SHA-256 hash, the same idea as storing password hashes.

Webhook signature: when we notify a merchant that a payment is paid, we sign
the message with HMAC-SHA256 using a secret only we and the merchant know.
The merchant recomputes the signature; if it matches, the message really
came from us and was not changed on the way. Stripe does exactly the same.
"""
import hashlib
import hmac
import secrets


def generate_api_key() -> str:
    return "sk_test_" + secrets.token_urlsafe(32)


def generate_webhook_secret() -> str:
    return "whsec_" + secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_signature(payload: bytes, secret: str, signature: str) -> bool:
    # compare_digest takes the same time for any input, which prevents
    # "timing attacks" that guess a signature character by character.
    return hmac.compare_digest(sign_payload(payload, secret), signature)

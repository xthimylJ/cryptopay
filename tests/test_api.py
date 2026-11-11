"""End-to-end API tests: they call the HTTP endpoints like a real client would."""
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import Payment
from tests.conftest import WALLET, auth, register

OK_HASH = "0x" + "ab" * 32
FAIL_HASH = "0x" + "ab" * 30 + "0000"


def create_payment(client, api_key, amount="0.001", order_id="ORDER-1"):
    r = client.post("/v1/payments", headers=auth(api_key),
                    json={"amount": amount, "order_id": order_id, "description": "Latte"})
    assert r.status_code == 201, r.text
    return r.json()


# ---------- Merchants ----------

def test_register_returns_keys_once(client):
    m = register(client)
    assert m["api_key"].startswith("sk_test_")
    assert m["webhook_secret"].startswith("whsec_")
    me = client.get("/v1/merchants/me", headers=auth(m["api_key"])).json()
    assert "api_key" not in me and me["id"] == m["id"]


def test_duplicate_email_is_rejected(client):
    register(client)
    r = client.post("/v1/merchants", json={"name": "X Shop", "email": "shop@test.kg",
                                           "wallet_address": WALLET})
    assert r.status_code == 409


def test_invalid_wallet_is_rejected(client):
    r = client.post("/v1/merchants", json={"name": "X Shop", "email": "a@b.kg",
                                           "wallet_address": "not-a-wallet"})
    assert r.status_code == 422


def test_requests_without_valid_key_are_unauthorized(client):
    assert client.get("/v1/payments").status_code == 401
    assert client.get("/v1/payments", headers=auth("sk_test_wrong")).status_code == 401


# ---------- Payments ----------

def test_create_payment(client, merchant):
    p = create_payment(client, merchant["api_key"], amount="0.0015")
    assert p["status"] == "pending"
    assert p["amount"] == "0.0015"
    assert p["amount_wei"] == "1500000000000000"
    assert p["to_address"] == WALLET
    assert p["checkout_url"].endswith(f"/pay/{p['id']}")


def test_amount_must_be_positive(client, merchant):
    r = client.post("/v1/payments", headers=auth(merchant["api_key"]), json={"amount": "0"})
    assert r.status_code == 422


def test_merchant_cannot_see_other_merchants_payment(client, merchant):
    p = create_payment(client, merchant["api_key"])
    other = register(client, email="other@test.kg")
    r = client.get(f"/v1/payments/{p['id']}", headers=auth(other["api_key"]))
    assert r.status_code == 404


def test_successful_payment_flow(client, merchant):
    p = create_payment(client, merchant["api_key"])
    info = client.get(f"/api/checkout/{p['id']}").json()
    assert info["merchant_name"] == "Test Shop" and info["status"] == "pending"

    r = client.post(f"/api/checkout/{p['id']}/transaction", json={"tx_hash": OK_HASH})
    assert r.status_code == 200
    assert r.json()["status"] == "paid"

    got = client.get(f"/v1/payments/{p['id']}", headers=auth(merchant["api_key"])).json()
    assert got["status"] == "paid" and got["paid_at"] is not None
    assert got["tx_hash"] == OK_HASH


def test_failed_transaction(client, merchant):
    p = create_payment(client, merchant["api_key"])
    r = client.post(f"/api/checkout/{p['id']}/transaction", json={"tx_hash": FAIL_HASH})
    assert r.json()["status"] == "failed"
    assert "Simulated failure" in r.json()["failure_reason"]


def test_same_transaction_cannot_pay_twice(client, merchant):
    p1 = create_payment(client, merchant["api_key"], order_id="A")
    p2 = create_payment(client, merchant["api_key"], order_id="B")
    client.post(f"/api/checkout/{p1['id']}/transaction", json={"tx_hash": OK_HASH})
    r = client.post(f"/api/checkout/{p2['id']}/transaction", json={"tx_hash": OK_HASH})
    assert r.status_code == 409


def test_paid_payment_rejects_new_transaction(client, merchant):
    p = create_payment(client, merchant["api_key"])
    client.post(f"/api/checkout/{p['id']}/transaction", json={"tx_hash": OK_HASH})
    r = client.post(f"/api/checkout/{p['id']}/transaction", json={"tx_hash": "0x" + "cd" * 32})
    assert r.status_code == 400


def test_invalid_tx_hash_format(client, merchant):
    p = create_payment(client, merchant["api_key"])
    r = client.post(f"/api/checkout/{p['id']}/transaction", json={"tx_hash": "hello"})
    assert r.status_code == 422


def test_cancel_pending_payment(client, merchant):
    p = create_payment(client, merchant["api_key"])
    r = client.post(f"/v1/payments/{p['id']}/cancel", headers=auth(merchant["api_key"]))
    assert r.json()["status"] == "canceled"
    r = client.post(f"/api/checkout/{p['id']}/transaction", json={"tx_hash": OK_HASH})
    assert r.status_code == 400


def test_payment_expires(client, merchant):
    p = create_payment(client, merchant["api_key"])
    # Move the deadline into the past directly in the database.
    with SessionLocal() as db:
        row = db.get(Payment, p["id"])
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert client.get(f"/api/checkout/{p['id']}").json()["status"] == "expired"
    r = client.post(f"/api/checkout/{p['id']}/transaction", json={"tx_hash": OK_HASH})
    assert r.status_code == 400


def test_unknown_payment_returns_404(client):
    assert client.get("/api/checkout/pay_doesnotexist").status_code == 404


def test_pages_and_health(client):
    assert client.get("/health").json()["status"] == "ok"
    for path in ["/", "/dashboard", "/pay/pay_x"]:
        r = client.get(path)
        assert r.status_code == 200 and "<html" in r.text

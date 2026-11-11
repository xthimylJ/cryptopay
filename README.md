# CryptoPay

A Stripe-like payment gateway that lets any online business accept **Ethereum (ETH)** payments.
A merchant creates a payment with one API call, the customer pays from **MetaMask** on the
**Sepolia testnet**, CryptoPay verifies the transaction on the blockchain and sends the merchant
a **signed webhook**.

Midterm project — *Advanced Software Engineering*, Ala-Too International University.

## Features

- Merchant registration with secret API keys (`sk_test_...`, stored only as SHA-256 hashes)
- REST API: create / list / get / cancel payments, hosted checkout links
- Checkout page with MetaMask: connects the wallet, switches to Sepolia, sends the exact amount
- On-chain verification over JSON-RPC: receiver, amount, success status, confirmations
- Payment state machine: `pending → confirming → paid | failed`, plus `expired` and `canceled`
- HMAC-SHA256 signed webhooks + a built-in demo shop that verifies them
- Replay protection: one transaction can pay only one payment
- Simulation mode (`BLOCKCHAIN_MODE=mock`) for demos without a wallet
- Merchant dashboard, Swagger docs at `/docs`, 32 automated tests

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2 · Pydantic 2 · httpx · PostgreSQL / SQLite · pytest · Render.com

## Project structure

```
app/
  main.py               app entry point, routers, HTML pages, error handler
  config.py             settings from environment variables
  database.py           SQLAlchemy engine and session
  models.py             DB tables: merchants, payments, webhook_events
  schemas.py            Pydantic request/response models (validation)
  security.py           API keys, HMAC webhook signatures
  repositories.py       all database access (Repository pattern)
  utils.py              ETH <-> wei conversion, IDs, validators
  services/
    merchant_service.py register / authenticate / update merchants
    payment_service.py  core business logic and the state machine
    webhook_service.py  WebhookNotifier interface + HTTP implementation
    errors.py           domain errors (mapped to HTTP codes in main.py)
  blockchain/
    base.py             BlockchainGateway interface (the SOLID core)
    sepolia.py          real Ethereum Sepolia verification via JSON-RPC
    mock.py             simulated blockchain
    factory.py          picks the gateway from BLOCKCHAIN_MODE
  api/
    deps.py             dependency injection wiring
    merchants.py, payments.py, checkout.py, demo_shop.py   HTTP routes
    presenters.py       DB object -> API response
static/                 index.html, dashboard.html, checkout.html, style.css
tests/                  pytest suite
docs/diagrams/          PlantUML / Graphviz sources and PNGs
render.yaml             Render Blueprint (infrastructure as code)
```

## Run locally (Windows)

```powershell
cd cryptopay
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000 — it starts in **simulation mode** with a local SQLite file.
To use the real Sepolia testnet locally:

```powershell
$env:BLOCKCHAIN_MODE="sepolia"; uvicorn app.main:app --reload
```

Run the tests:

```powershell
pytest -v
```

## Deploy to Render

1. Push this folder to a new GitHub repository.
2. On https://render.com sign in with GitHub → **New → Blueprint** → choose the repository.
3. Render reads `render.yaml`, creates the PostgreSQL database and the web service → **Apply**.
4. After the build finishes (~3–5 min) open `https://<your-service>.onrender.com`.

The free instance sleeps after ~15 minutes without traffic; the first request then takes up to a minute.
To demo without MetaMask, set `BLOCKCHAIN_MODE=mock` in the service's **Environment** tab.

## API in 30 seconds

```bash
# 1. Register (or use the dashboard)
curl -X POST $BASE/v1/merchants -H "Content-Type: application/json" \
  -d '{"name":"Coffee Shop","email":"me@shop.kg","wallet_address":"0xYourWallet...","webhook_url":"'$BASE'/demo/webhook-receiver"}'

# 2. Create a payment
curl -X POST $BASE/v1/payments -H "Authorization: Bearer sk_test_..." \
  -H "Content-Type: application/json" -d '{"amount":"0.0001","order_id":"ORDER-1"}'

# 3. Send the customer to checkout_url from the response
```

## Verifying a webhook (merchant side, Python)

```python
import hmac, hashlib
expected = hmac.new(WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, request.headers["X-CryptoPay-Signature"]):
    reject()
```

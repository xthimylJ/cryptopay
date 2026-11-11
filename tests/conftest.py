"""
Test setup. Runs before every test file.

We point the app at a separate temporary SQLite database and force the
mock blockchain, so tests are fast, repeatable and need no internet.
"""
import os
import tempfile

_db_file = os.path.join(tempfile.gettempdir(), "cryptopay_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["BLOCKCHAIN_MODE"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

WALLET = "0x1111111111111111111111111111111111111111"


@pytest.fixture
def client():
    # Fresh empty tables for every test -> tests don't affect each other.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def register(client, email="shop@test.kg", webhook_url=None):
    response = client.post("/v1/merchants", json={
        "name": "Test Shop", "email": email,
        "wallet_address": WALLET, "webhook_url": webhook_url,
    })
    assert response.status_code == 201, response.text
    return response.json()


def auth(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


@pytest.fixture
def merchant(client):
    return register(client)

import time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from ecommerce.payments.config import settings
from ecommerce.payments.main import app
from ecommerce.payments.store import store


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "latency_ms", 0)
    store.clear()
    with TestClient(app) as client:
        yield client
    store.clear()


def pay(client, order_id=1, amount="24.98"):
    return client.post("/payments", json={"order_id": order_id, "amount": amount})


def test_healthz(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_payment_succeeds_when_failure_rate_is_zero(client, monkeypatch):
    monkeypatch.setattr(settings, "failure_rate", 0.0)

    response = pay(client)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "SUCCEEDED"
    assert body["order_id"] == 1
    assert body["amount"] == "24.98"
    assert body["payment_id"]


def test_payment_fails_when_failure_rate_is_one(client, monkeypatch):
    monkeypatch.setattr(settings, "failure_rate", 1.0)

    response = pay(client)

    assert response.status_code == 201
    assert response.json()["status"] == "FAILED"


def test_each_order_gets_a_new_payment_id(client, monkeypatch):
    monkeypatch.setattr(settings, "failure_rate", 0.0)

    first = pay(client, order_id=1).json()["payment_id"]
    second = pay(client, order_id=2).json()["payment_id"]

    assert first != second


def test_repeat_payment_returns_stored_result(client, monkeypatch):
    monkeypatch.setattr(settings, "failure_rate", 0.0)
    first = pay(client)

    response = pay(client)

    assert response.status_code == 200
    assert response.json() == first.json()


def test_repeat_payment_does_not_reroll_a_failure(client, monkeypatch):
    monkeypatch.setattr(settings, "failure_rate", 1.0)
    pay(client)
    monkeypatch.setattr(settings, "failure_rate", 0.0)

    response = pay(client)

    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"


def test_repeat_payment_with_different_amount_is_rejected(client):
    pay(client, amount="24.98")

    response = pay(client, amount="10.00")

    assert response.status_code == 409


def test_payment_in_progress_is_rejected(client):
    store.reserve(1, Decimal("24.98"))

    response = pay(client, amount="24.98")

    assert response.status_code == 409


def test_latency_is_applied(client, monkeypatch):
    monkeypatch.setattr(settings, "latency_ms", 200)

    start = time.perf_counter()
    pay(client)

    assert time.perf_counter() - start >= 0.2


@pytest.mark.parametrize(
    "payload",
    [
        {"order_id": 0, "amount": "1.00"},
        {"order_id": 1, "amount": "0"},
        {"order_id": 1, "amount": "1.001"},
        {"order_id": 1},
    ],
    ids=["zero-order-id", "zero-amount", "too-many-decimals", "missing-amount"],
)
def test_rejects_invalid_payload(client, payload):
    response = client.post("/payments", json=payload)

    assert response.status_code == 422

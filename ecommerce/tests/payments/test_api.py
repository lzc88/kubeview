import time
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update

from ecommerce.payments import providers
from ecommerce.payments.config import settings
from ecommerce.payments.db.models import Payment, PaymentStatus


def pay(client, order_id=1, amount="24.98"):
    return client.post("/payments", json={"order_id": order_id, "amount": amount})


def add_pending(session, order_id=1, amount="24.98", age=timedelta(0), **fields):
    payment = Payment(
        order_id=order_id, amount=Decimal(amount), provider="fake", **fields
    )
    session.add(payment)
    session.flush()
    session.execute(
        update(Payment)
        .where(Payment.id == payment.id)
        .values(updated_at=func.now() - age)
    )
    session.commit()
    return payment


def stored(session, order_id=1):
    return session.scalars(select(Payment).where(Payment.order_id == order_id)).one()


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
    assert body["provider"] == "fake"
    assert body["id"]


def test_payment_fails_when_failure_rate_is_one(client, monkeypatch):
    monkeypatch.setattr(settings, "failure_rate", 1.0)

    response = pay(client)

    assert response.status_code == 201
    assert response.json()["status"] == "FAILED"


def test_payment_is_persisted(client, session, monkeypatch):
    monkeypatch.setattr(settings, "failure_rate", 0.0)

    body = pay(client).json()

    payment = stored(session)
    assert str(payment.id) == body["id"]
    assert payment.status == PaymentStatus.SUCCEEDED


def test_each_order_gets_a_new_payment_id(client, monkeypatch):
    monkeypatch.setattr(settings, "failure_rate", 0.0)

    first = pay(client, order_id=1).json()["id"]
    second = pay(client, order_id=2).json()["id"]

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


def test_payment_in_progress_is_rejected(client, session):
    add_pending(session)

    response = pay(client)

    assert response.status_code == 409


def test_stale_pending_payment_is_retried(client, session, monkeypatch):
    monkeypatch.setattr(settings, "failure_rate", 0.0)
    pending = add_pending(session, age=timedelta(minutes=5))

    response = pay(client)

    assert response.status_code == 201
    assert response.json()["id"] == str(pending.id)
    assert response.json()["status"] == "SUCCEEDED"


def test_stale_pending_payment_with_different_amount_is_rejected(client, session):
    add_pending(session, amount="24.98", age=timedelta(minutes=5))

    response = pay(client, amount="10.00")

    assert response.status_code == 409
    assert stored(session).status == PaymentStatus.PENDING


def test_provider_unavailable_leaves_payment_pending(client, session, monkeypatch):
    def unavailable(order_id, amount):
        raise providers.ProviderUnavailable("connection refused")

    monkeypatch.setattr(providers, "charge", unavailable)

    response = pay(client)

    assert response.status_code == 503
    assert stored(session).status == PaymentStatus.PENDING


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


CHECKOUT = providers.ChargeResult(
    PaymentStatus.PENDING,
    checkout_session_id="cs_test_123",
    checkout_url="https://checkout.stripe.com/c/pay/cs_test_123",
)


@pytest.fixture
def checkout(monkeypatch):
    calls = []

    def create(order_id, amount):
        calls.append(order_id)
        return CHECKOUT

    monkeypatch.setattr(providers, "charge", create)
    return calls


def test_checkout_payment_is_accepted_with_url(client, checkout):
    response = pay(client)

    assert response.status_code == 202
    assert response.json()["status"] == "PENDING"
    assert response.json()["checkout_url"] == CHECKOUT.checkout_url


def test_repeat_checkout_returns_the_same_url(client, checkout):
    first = pay(client)

    retry = pay(client)

    assert retry.status_code == 202
    assert retry.json() == first.json()
    assert checkout == [1]


def test_open_checkout_is_never_reclaimed(client, session, checkout):
    add_pending(
        session,
        age=timedelta(hours=1),
        checkout_session_id=CHECKOUT.checkout_session_id,
        checkout_url=CHECKOUT.checkout_url,
    )

    response = pay(client)

    assert response.status_code == 202
    assert response.json()["checkout_url"] == CHECKOUT.checkout_url
    assert checkout == []

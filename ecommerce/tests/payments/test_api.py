from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update

from ecommerce.payments import providers
from ecommerce.payments.db.models import Payment, PaymentStatus


def pay(client, order_id=1, amount="24.98"):
    return client.post("/payments", json={"order_id": order_id, "amount": amount})


def add_payment(session, order_id=1, amount="24.98", age=timedelta(0), **fields):
    payment = Payment(
        order_id=order_id, amount=Decimal(amount), provider="stripe", **fields
    )
    session.add(payment)
    session.flush()
    session.execute(
        update(Payment)
        .where(Payment.id == payment.id)
        .values(created_at=func.now() - age, updated_at=func.now() - age)
    )
    session.commit()
    return payment


CHECKOUT = providers.ChargeResult(
    PaymentStatus.PENDING,
    checkout_session_id="cs_test_123",
    checkout_url="https://checkout.stripe.com/c/pay/cs_test_123",
)


@pytest.fixture(autouse=True)
def checkout(monkeypatch):
    calls = []

    def create(order_id, amount, started_at):
        calls.append(order_id)
        return CHECKOUT

    monkeypatch.setattr(providers, "charge", create)
    return calls


def stored(session, order_id=1):
    return session.scalars(select(Payment).where(Payment.order_id == order_id)).one()


def test_healthz(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_payment_is_accepted_with_checkout_url(client):
    response = pay(client)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["order_id"] == 1
    assert body["amount"] == "24.98"
    assert body["provider"] == "stripe"
    assert body["checkout_url"] == CHECKOUT.checkout_url
    assert body["id"]


def test_payment_is_persisted(client, session):
    body = pay(client).json()

    payment = stored(session)
    assert str(payment.id) == body["id"]
    assert payment.status == PaymentStatus.PENDING
    assert payment.checkout_session_id == CHECKOUT.checkout_session_id


def test_each_order_gets_a_new_payment_id(client):
    first = pay(client, order_id=1).json()["id"]
    second = pay(client, order_id=2).json()["id"]

    assert first != second


def test_repeat_checkout_returns_the_same_url(client, checkout):
    first = pay(client)

    retry = pay(client)

    assert retry.status_code == 202
    assert retry.json() == first.json()
    assert checkout == [1]


def test_settled_payment_is_returned_without_charging(client, session, checkout):
    add_payment(session, status=PaymentStatus.FAILED)

    response = pay(client)

    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert checkout == []


def test_repeat_payment_with_different_amount_is_rejected(client):
    pay(client, amount="24.98")

    response = pay(client, amount="10.00")

    assert response.status_code == 409


def test_payment_in_progress_is_rejected(client, session):
    add_payment(session)

    response = pay(client)

    assert response.status_code == 409


def test_stale_pending_payment_is_retried(client, session, checkout):
    pending = add_payment(session, age=timedelta(minutes=5))

    response = pay(client)

    assert response.status_code == 202
    assert response.json()["id"] == str(pending.id)
    assert response.json()["checkout_url"] == CHECKOUT.checkout_url
    assert checkout == [1]


def test_payment_without_checkout_past_deadline_fails(client, session, checkout):
    add_payment(session, age=timedelta(minutes=11))

    response = pay(client)

    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert checkout == []


def test_rejected_checkout_fails_the_payment(client, session, monkeypatch):
    monkeypatch.setattr(
        providers,
        "charge",
        lambda order_id, amount, started_at: providers.ChargeResult(
            PaymentStatus.FAILED
        ),
    )

    response = pay(client)

    assert response.status_code == 201
    assert response.json()["status"] == "FAILED"
    assert stored(session).status == PaymentStatus.FAILED


def test_stale_pending_payment_with_different_amount_is_rejected(client, session):
    add_payment(session, amount="24.98", age=timedelta(minutes=5))

    response = pay(client, amount="10.00")

    assert response.status_code == 409
    assert stored(session).status == PaymentStatus.PENDING


def test_provider_unavailable_leaves_payment_pending(client, session, monkeypatch):
    def unavailable(order_id, amount, started_at):
        raise providers.ProviderUnavailable("connection refused")

    monkeypatch.setattr(providers, "charge", unavailable)

    response = pay(client)

    assert response.status_code == 503
    assert stored(session).status == PaymentStatus.PENDING


def test_open_checkout_is_never_reclaimed(client, session, checkout):
    add_payment(
        session,
        age=timedelta(hours=1),
        checkout_session_id=CHECKOUT.checkout_session_id,
        checkout_url=CHECKOUT.checkout_url,
    )

    response = pay(client)

    assert response.status_code == 202
    assert response.json()["checkout_url"] == CHECKOUT.checkout_url
    assert checkout == []


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

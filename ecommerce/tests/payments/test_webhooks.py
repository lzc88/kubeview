import hashlib
import hmac
import json
import time
from decimal import Decimal

import pytest
import stripe
from pydantic import SecretStr
from sqlalchemy import select

from ecommerce.payments import orders_client, providers
from ecommerce.payments.config import settings
from ecommerce.payments.db.models import Payment, PaymentStatus

SECRET = "whsec_test_secret"


@pytest.fixture
def send(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_api_key", SecretStr("sk_test_dummy"))
    monkeypatch.setattr(settings, "stripe_webhook_secret", SecretStr(SECRET))
    providers.stripe_client.cache_clear()

    def post(event_type, order_id=1, payment_status="paid", secret=SECRET):
        payload = json.dumps(
            {
                "id": "evt_test",
                "object": "event",
                "api_version": stripe.api_version,
                "type": event_type,
                "data": {
                    "object": {
                        "id": "cs_test_123",
                        "object": "checkout.session",
                        "client_reference_id": str(order_id),
                        "payment_status": payment_status,
                        "payment_intent": "pi_test_123",
                    }
                },
            }
        )
        timestamp = int(time.time())
        signature = hmac.new(
            secret.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256
        ).hexdigest()
        return client.post(
            "/webhooks/stripe",
            content=payload,
            headers={
                "Stripe-Signature": f"t={timestamp},v1={signature}",
                "Content-Type": "application/json",
            },
        )

    yield post
    providers.stripe_client.cache_clear()


@pytest.fixture
def notified(monkeypatch):
    calls = []
    monkeypatch.setattr(
        orders_client, "notify", lambda order_id, status: calls.append((order_id, status))
    )
    return calls


@pytest.fixture
def open_checkout(session):
    payment = Payment(
        order_id=1,
        amount=Decimal("24.98"),
        provider="stripe",
        checkout_session_id="cs_test_123",
        checkout_url="https://checkout.stripe.com/c/pay/cs_test_123",
    )
    session.add(payment)
    session.commit()
    return payment


def status_of(session, order_id=1):
    payment = session.scalars(select(Payment).where(Payment.order_id == order_id)).one()
    session.refresh(payment)
    return payment.status


def test_completed_checkout_marks_payment_succeeded(send, notified, session, open_checkout):
    response = send("checkout.session.completed")

    assert response.status_code == 200
    assert status_of(session) == PaymentStatus.SUCCEEDED
    assert open_checkout.provider_payment_id == "pi_test_123"
    assert notified == [(1, "SUCCEEDED")]


def test_completed_but_unpaid_checkout_waits(send, notified, session, open_checkout):
    send("checkout.session.completed", payment_status="unpaid")

    assert status_of(session) == PaymentStatus.PENDING
    assert notified == []


def test_async_payment_succeeded(send, notified, session, open_checkout):
    send("checkout.session.async_payment_succeeded", payment_status="paid")

    assert status_of(session) == PaymentStatus.SUCCEEDED


@pytest.mark.parametrize(
    "event_type",
    ["checkout.session.expired", "checkout.session.async_payment_failed"],
)
def test_expired_or_failed_checkout_marks_payment_failed(
    send, notified, session, open_checkout, event_type
):
    send(event_type, payment_status="unpaid")

    assert status_of(session) == PaymentStatus.FAILED
    assert notified == [(1, "FAILED")]


def test_redelivered_event_notifies_again_without_changing(
    send, notified, session, open_checkout
):
    send("checkout.session.completed")

    response = send("checkout.session.completed")

    assert response.status_code == 200
    assert status_of(session) == PaymentStatus.SUCCEEDED
    assert notified == [(1, "SUCCEEDED"), (1, "SUCCEEDED")]


def test_late_expiry_does_not_overwrite_success(send, notified, session, open_checkout):
    send("checkout.session.completed")

    send("checkout.session.expired", payment_status="unpaid")

    assert status_of(session) == PaymentStatus.SUCCEEDED
    assert notified[-1] == (1, "SUCCEEDED")


def test_bad_signature_is_rejected(send, notified, session, open_checkout):
    response = send("checkout.session.completed", secret="whsec_wrong")

    assert response.status_code == 400
    assert status_of(session) == PaymentStatus.PENDING
    assert notified == []


def test_irrelevant_event_is_acknowledged(send, notified, session, open_checkout):
    response = send("payment_intent.created")

    assert response.status_code == 200
    assert status_of(session) == PaymentStatus.PENDING
    assert notified == []


def test_event_for_unknown_order_is_acknowledged(send, notified):
    response = send("checkout.session.completed", order_id=424242)

    assert response.status_code == 200
    assert notified == []


def test_orders_unavailable_asks_stripe_to_retry(send, session, open_checkout, monkeypatch):
    def unavailable(order_id, status):
        raise orders_client.OrdersUnavailable("connection refused")

    monkeypatch.setattr(orders_client, "notify", unavailable)

    response = send("checkout.session.completed")

    assert response.status_code == 503
    assert status_of(session) == PaymentStatus.SUCCEEDED

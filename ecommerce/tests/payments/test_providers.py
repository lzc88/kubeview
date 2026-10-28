import os
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import stripe

from ecommerce.payments import providers
from ecommerce.payments.config import settings
from ecommerce.payments.db.models import PaymentStatus

STARTED = datetime(2026, 1, 1, tzinfo=UTC)
PAYMENT_ID = UUID("6f1c2d3e-4a5b-4c6d-8e7f-0a1b2c3d4e5f")

SESSION = SimpleNamespace(
    id="cs_test_123", url="https://checkout.stripe.com/c/pay/cs_test_123"
)


class FakeSessions:

    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def create(self, params, options):
        self.calls.append((params, options))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def sessions(monkeypatch):
    def use(outcome):
        fake = FakeSessions(outcome)
        checkout = SimpleNamespace(sessions=fake)
        client = SimpleNamespace(v1=SimpleNamespace(checkout=checkout))
        monkeypatch.setattr(providers, "stripe_client", lambda: client)
        return fake

    return use


def test_charge_returns_pending_checkout(sessions):
    sessions(SESSION)

    result = providers.charge(PAYMENT_ID, 42, Decimal("24.98"), STARTED)

    assert result == providers.ChargeResult(
        PaymentStatus.PENDING,
        checkout_session_id=SESSION.id,
        checkout_url=SESSION.url,
    )


def test_checkout_request_is_idempotent_per_payment(sessions):
    fake = sessions(SESSION)

    providers.charge(PAYMENT_ID, 42, Decimal("24.98"), STARTED)

    params, options = fake.calls[0]
    assert params["mode"] == "payment"
    assert params["line_items"][0]["price_data"]["unit_amount"] == 2498
    assert params["line_items"][0]["price_data"]["currency"] == settings.stripe_currency
    assert params["client_reference_id"] == "42"
    assert "42" in params["success_url"]
    assert "payment_method_types" not in params
    assert params["expires_at"] == int((STARTED + timedelta(minutes=60)).timestamp())
    assert options == {"idempotency_key": f"checkout-create:{PAYMENT_ID}"}


def test_checkout_request_is_deterministic(sessions):
    fake = sessions(SESSION)

    providers.charge(PAYMENT_ID, 42, Decimal("24.98"), STARTED)
    providers.charge(PAYMENT_ID, 42, Decimal("24.98"), STARTED)

    assert fake.calls[0] == fake.calls[1]


def test_rejected_request_fails_the_payment(sessions):
    sessions(stripe.InvalidRequestError("amount too small", param="unit_amount"))

    result = providers.charge(PAYMENT_ID, 42, Decimal("0.10"), STARTED)

    assert result == providers.ChargeResult(PaymentStatus.FAILED)


def test_payments_for_the_same_order_get_distinct_keys(sessions):
    fake = sessions(SESSION)

    providers.charge(uuid4(), 42, Decimal("24.98"), STARTED)
    providers.charge(uuid4(), 42, Decimal("24.98"), STARTED)

    assert fake.calls[0][1] != fake.calls[1][1]


def test_reused_key_with_different_params_fails_the_payment(sessions):
    sessions(stripe.IdempotencyError("idempotency key reused with different params"))

    result = providers.charge(PAYMENT_ID, 42, Decimal("24.98"), STARTED)

    assert result == providers.ChargeResult(PaymentStatus.FAILED)


def test_stripe_outage_is_unavailable(sessions):
    sessions(stripe.APIConnectionError("connection refused"))

    with pytest.raises(providers.ProviderUnavailable):
        providers.charge(PAYMENT_ID, 42, Decimal("24.98"), STARTED)


@pytest.mark.skipif(
    not os.environ.get("STRIPE_LIVE_TESTS") or settings.stripe_api_key is None,
    reason="set STRIPE_LIVE_TESTS=1 and STRIPE_API_KEY to call the Stripe sandbox",
)
def test_stripe_sandbox_checkout_is_idempotent():
    payment_id = uuid4()
    order_id = random.randint(10**9, 2 * 10**9)

    started_at = datetime.now(UTC)

    first = providers.charge(payment_id, order_id, Decimal("24.98"), started_at)
    retry = providers.charge(payment_id, order_id, Decimal("24.98"), started_at)

    assert first.checkout_url
    assert retry == first

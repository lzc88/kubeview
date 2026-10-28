import os
import random
from decimal import Decimal
from types import SimpleNamespace

import pytest
import stripe

from ecommerce.payments import providers
from ecommerce.payments.config import settings
from ecommerce.payments.db.models import PaymentStatus

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

    result = providers.charge(42, Decimal("24.98"))

    assert result == providers.ChargeResult(
        PaymentStatus.PENDING,
        checkout_session_id=SESSION.id,
        checkout_url=SESSION.url,
    )


def test_checkout_request_is_idempotent_per_order(sessions):
    fake = sessions(SESSION)

    providers.charge(42, Decimal("24.98"))

    params, options = fake.calls[0]
    assert params["mode"] == "payment"
    assert params["line_items"][0]["price_data"]["unit_amount"] == 2498
    assert params["line_items"][0]["price_data"]["currency"] == settings.stripe_currency
    assert params["client_reference_id"] == "42"
    assert "42" in params["success_url"]
    assert "payment_method_types" not in params
    assert options == {"idempotency_key": "order-42"}


def test_checkout_request_is_deterministic(sessions):
    fake = sessions(SESSION)

    providers.charge(42, Decimal("24.98"))
    providers.charge(42, Decimal("24.98"))

    assert fake.calls[0] == fake.calls[1]


def test_stripe_outage_is_unavailable(sessions):
    sessions(stripe.APIConnectionError("connection refused"))

    with pytest.raises(providers.ProviderUnavailable):
        providers.charge(42, Decimal("24.98"))


@pytest.mark.skipif(
    not os.environ.get("STRIPE_LIVE_TESTS") or settings.stripe_api_key is None,
    reason="set STRIPE_LIVE_TESTS=1 and STRIPE_API_KEY to call the Stripe sandbox",
)
def test_stripe_sandbox_checkout_is_idempotent():
    order_id = random.randint(10**9, 2 * 10**9)

    first = providers.charge(order_id, Decimal("24.98"))
    retry = providers.charge(order_id, Decimal("24.98"))

    assert first.checkout_url
    assert retry == first

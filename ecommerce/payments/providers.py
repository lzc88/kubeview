import random
import time
from dataclasses import dataclass
from decimal import Decimal
from functools import cache

import stripe

from ecommerce.payments.config import settings
from ecommerce.payments.db.models import PaymentStatus

INTEGRATION_IDENTIFIER = "kubeview-checkout-qmrvtzke"


class ProviderUnavailable(Exception):
    pass


@dataclass
class ChargeResult:
    status: PaymentStatus
    provider_payment_id: str | None = None
    checkout_session_id: str | None = None
    checkout_url: str | None = None


def charge(order_id: int, amount: Decimal) -> ChargeResult:

    if settings.provider == "stripe":
        return create_checkout(order_id, amount)

    return charge_fake()


def charge_fake() -> ChargeResult:

    time.sleep(settings.latency_ms / 1000)

    succeeded = random.random() >= settings.failure_rate

    return ChargeResult(PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED)


def create_checkout(order_id: int, amount: Decimal) -> ChargeResult:

    try:
        checkout = stripe_client().v1.checkout.sessions.create(
            params={
                "mode": "payment",
                "line_items": [
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": settings.stripe_currency,
                            "unit_amount": int(amount * 100),
                            "product_data": {"name": f"Order {order_id}"},
                        },
                    }
                ],
                "client_reference_id": str(order_id),
                "metadata": {"order_id": str(order_id)},
                "payment_intent_data": {"metadata": {"order_id": str(order_id)}},
                "success_url": settings.stripe_success_url.replace(
                    "{order_id}", str(order_id)
                ),
                "integration_identifier": INTEGRATION_IDENTIFIER,
            },
            options={"idempotency_key": f"order-{order_id}"},
        )

    except stripe.StripeError as exc:
        raise ProviderUnavailable(str(exc)) from exc

    return ChargeResult(
        PaymentStatus.PENDING,
        checkout_session_id=checkout.id,
        checkout_url=checkout.url,
    )


@cache
def stripe_client() -> stripe.StripeClient:

    if settings.stripe_api_key is None:
        raise ProviderUnavailable("STRIPE_API_KEY is not set")

    return stripe.StripeClient(
        settings.stripe_api_key.get_secret_value(),
        http_client=stripe.HTTPXClient(
            timeout=settings.stripe_timeout_seconds, allow_sync_methods=True
        ),
    )

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import httpx

from ecommerce.orders.config import settings

PaymentStatus = Literal["PENDING", "SUCCEEDED", "FAILED"]


class PaymentsUnavailable(Exception):
    pass


@dataclass
class PaymentResult:
    status: PaymentStatus
    checkout_url: str | None = None


def charge(order_id: int, amount: Decimal) -> PaymentResult:

    try:
        response = httpx.post(
            f"{settings.payments_url}/payments",
            json={"order_id": order_id, "amount": str(amount)},
            timeout=settings.payments_timeout_seconds,
        )

        response.raise_for_status()

    except httpx.HTTPError as exc:
        raise PaymentsUnavailable(str(exc)) from exc

    body = response.json()

    return PaymentResult(status=body["status"], checkout_url=body.get("checkout_url"))

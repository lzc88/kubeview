from decimal import Decimal

import httpx

from ecommerce.orders.config import settings


class PaymentsUnavailable(Exception):
    pass


def charge(order_id: int, amount: Decimal) -> bool:
    try:
        response = httpx.post(
            f"{settings.payments_url}/payments",
            json={"order_id": order_id, "amount": str(amount)},
            timeout=settings.payments_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise PaymentsUnavailable(str(exc)) from exc
    return response.json()["status"] == "SUCCEEDED"

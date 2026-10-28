import httpx

from ecommerce.payments.config import settings


class OrdersUnavailable(Exception):
    pass


def notify(order_id: int, status: str) -> None:

    try:
        response = httpx.post(
            f"{settings.orders_url}/orders/{order_id}/payment-result",
            json={"status": status},
            timeout=settings.orders_timeout_seconds,
        )

        response.raise_for_status()

    except httpx.HTTPError as exc:
        raise OrdersUnavailable(str(exc)) from exc

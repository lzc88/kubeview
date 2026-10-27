from decimal import Decimal

import pytest

from ecommerce.orders import payments_client
from ecommerce.orders.config import settings


def test_unreachable_payments_raises_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "payments_url", "http://127.0.0.1:1")

    with pytest.raises(payments_client.PaymentsUnavailable):
        payments_client.charge(1, Decimal("1.00"))

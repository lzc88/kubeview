from uuid import uuid4

import pytest

from ecommerce.orders import payments_client


@pytest.fixture
def order(client, monkeypatch):
    monkeypatch.setattr(
        payments_client,
        "charge",
        lambda order_id, amount: payments_client.PaymentResult(
            "PENDING", checkout_url="https://checkout"
        ),
    )
    created = client.post(
        "/orders",
        json={"user_id": "u1", "items": [{"sku": "SKU-1", "qty": 1, "unit_price": "5.00"}]},
        headers={"Idempotency-Key": str(uuid4())},
    ).json()
    client.post(f"/orders/{created['id']}/pay")
    return created


def notify(client, order_id, status):
    return client.post(f"/orders/{order_id}/payment-result", json={"status": status})


def test_succeeded_payment_marks_order_paid(client, order):
    response = notify(client, order["id"], "SUCCEEDED")

    assert response.status_code == 200
    assert response.json()["status"] == "PAID"


def test_failed_payment_marks_order_failed(client, order):
    response = notify(client, order["id"], "FAILED")

    assert response.json()["status"] == "PAYMENT_FAILED"


def test_repeated_notification_is_idempotent(client, order):
    notify(client, order["id"], "SUCCEEDED")

    response = notify(client, order["id"], "SUCCEEDED")

    assert response.status_code == 200
    assert response.json()["status"] == "PAID"


def test_late_conflicting_notification_does_not_overwrite(client, order):
    notify(client, order["id"], "SUCCEEDED")

    response = notify(client, order["id"], "FAILED")

    assert response.json()["status"] == "PAID"


def test_notification_for_unknown_order(client):
    response = notify(client, 999999, "SUCCEEDED")

    assert response.status_code == 404


def test_notification_rejects_pending_status(client, order):
    response = notify(client, order["id"], "PENDING")

    assert response.status_code == 422

from uuid import uuid4

import pytest

from ecommerce.orders import payments_client

SUCCEEDED = payments_client.PaymentResult("SUCCEEDED")
FAILED = payments_client.PaymentResult("FAILED")
CHECKOUT = payments_client.PaymentResult(
    "PENDING", checkout_url="https://checkout.stripe.com/c/pay/cs_test_123"
)


def make_order(client):
    items = [{"sku": "SKU-1", "qty": 2, "unit_price": "9.99"}]
    return client.post(
        "/orders",
        json={"user_id": "u1", "items": items},
        headers={"Idempotency-Key": str(uuid4())},
    ).json()


@pytest.fixture
def charges(monkeypatch):
    calls = []

    def set_result(result):
        def fake_charge(order_id, amount):
            calls.append((order_id, amount))
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(payments_client, "charge", fake_charge)

    set_result.calls = calls
    return set_result


def test_pay_marks_order_paid(client, charges):
    charges(SUCCEEDED)
    order = make_order(client)

    response = client.post(f"/orders/{order['id']}/pay")

    assert response.status_code == 200
    assert response.json()["status"] == "PAID"
    assert [(order_id, str(amount)) for order_id, amount in charges.calls] == [
        (order["id"], "19.98")
    ]


def test_declined_payment_marks_order_failed(client, charges):
    charges(FAILED)
    order = make_order(client)

    response = client.post(f"/orders/{order['id']}/pay")

    assert response.status_code == 200
    assert response.json()["status"] == "PAYMENT_FAILED"


def test_payments_unavailable_leaves_order_processing(client, charges):
    charges(payments_client.PaymentsUnavailable("connection refused"))
    order = make_order(client)

    response = client.post(f"/orders/{order['id']}/pay")

    assert response.status_code == 202
    assert response.json()["status"] == "PROCESSING"
    assert client.get(f"/orders/{order['id']}").json()["status"] == "PROCESSING"


def test_paying_a_processing_order_retries_the_payment(client, charges):
    charges(payments_client.PaymentsUnavailable("connection refused"))
    order = make_order(client)
    client.post(f"/orders/{order['id']}/pay")
    charges(SUCCEEDED)

    response = client.post(f"/orders/{order['id']}/pay")

    assert response.status_code == 200
    assert response.json()["status"] == "PAID"


def test_checkout_leaves_order_processing_with_url(client, charges):
    charges(CHECKOUT)
    order = make_order(client)

    response = client.post(f"/orders/{order['id']}/pay")

    assert response.status_code == 202
    assert response.json()["status"] == "PROCESSING"
    assert response.json()["checkout_url"] == CHECKOUT.checkout_url


def test_repeat_pay_returns_the_same_checkout_url(client, charges):
    charges(CHECKOUT)
    order = make_order(client)
    first = client.post(f"/orders/{order['id']}/pay")

    retry = client.post(f"/orders/{order['id']}/pay")

    assert retry.status_code == 202
    assert retry.json()["checkout_url"] == first.json()["checkout_url"]


def test_paying_twice_is_rejected(client, charges):
    charges(SUCCEEDED)
    order = make_order(client)
    client.post(f"/orders/{order['id']}/pay")

    response = client.post(f"/orders/{order['id']}/pay")

    assert response.status_code == 409
    assert len(charges.calls) == 1


def test_pay_missing_order(client, charges):
    charges(SUCCEEDED)

    response = client.post("/orders/999999/pay")

    assert response.status_code == 404
    assert charges.calls == []

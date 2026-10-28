import pytest

from ecommerce.orders import payments_client


def make_order(client):
    items = [{"sku": "SKU-1", "qty": 2, "unit_price": "9.99"}]
    return client.post("/orders", json={"user_id": "u1", "items": items}).json()


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
    charges(True)
    order = make_order(client)

    response = client.post(f"/orders/{order['id']}/pay")

    assert response.status_code == 200
    assert response.json()["status"] == "PAID"
    assert [(order_id, str(amount)) for order_id, amount in charges.calls] == [
        (order["id"], "19.98")
    ]


def test_declined_payment_marks_order_failed(client, charges):
    charges(False)
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


def test_paying_a_processing_order_is_rejected(client, charges):
    charges(payments_client.PaymentsUnavailable("connection refused"))
    order = make_order(client)
    client.post(f"/orders/{order['id']}/pay")

    response = client.post(f"/orders/{order['id']}/pay")

    assert response.status_code == 409
    assert len(charges.calls) == 1


def test_paying_twice_is_rejected(client, charges):
    charges(True)
    order = make_order(client)
    client.post(f"/orders/{order['id']}/pay")

    response = client.post(f"/orders/{order['id']}/pay")

    assert response.status_code == 409
    assert len(charges.calls) == 1


def test_pay_missing_order(client, charges):
    charges(True)

    response = client.post("/orders/999999/pay")

    assert response.status_code == 404
    assert charges.calls == []

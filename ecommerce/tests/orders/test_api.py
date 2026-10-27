import pytest


def make_order(client, user_id="u1", items=None):
    items = items or [
        {"sku": "SKU-1", "qty": 2, "unit_price": "9.99"},
        {"sku": "SKU-2", "qty": 1, "unit_price": "5.00"},
    ]
    return client.post("/orders", json={"user_id": user_id, "items": items})


def test_healthz(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_order(client):
    response = make_order(client)

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == "u1"
    assert body["status"] == "PENDING"
    assert body["total"] == "24.98"
    assert {item["sku"] for item in body["items"]} == {"SKU-1", "SKU-2"}
    assert body["created_at"] is not None


def test_get_order(client):
    order_id = make_order(client).json()["id"]

    response = client.get(f"/orders/{order_id}")

    assert response.status_code == 200
    assert response.json()["id"] == order_id
    assert len(response.json()["items"]) == 2


def test_get_order_not_found(client):
    response = client.get("/orders/999999")

    assert response.status_code == 404


def test_list_orders_filters_by_user_newest_first(client):
    first = make_order(client, user_id="u1").json()["id"]
    second = make_order(client, user_id="u1").json()["id"]
    make_order(client, user_id="u2")

    response = client.get("/orders", params={"user_id": "u1"})

    assert response.status_code == 200
    assert [order["id"] for order in response.json()] == [second, first]


@pytest.mark.parametrize(
    "items",
    [
        [],
        [{"sku": "SKU-1", "qty": 0, "unit_price": "1.00"}],
        [{"sku": "SKU-1", "qty": 1, "unit_price": "0"}],
        [{"sku": "SKU-1", "qty": 1, "unit_price": "1.001"}],
        [{"sku": "", "qty": 1, "unit_price": "1.00"}],
        [
            {"sku": "SKU-1", "qty": 1, "unit_price": "1.00"},
            {"sku": "SKU-1", "qty": 2, "unit_price": "1.00"},
        ],
    ],
    ids=[
        "no-items",
        "zero-qty",
        "zero-price",
        "too-many-decimals",
        "empty-sku",
        "duplicate-sku",
    ],
)
def test_create_order_rejects_invalid_items(client, items):
    response = client.post("/orders", json={"user_id": "u1", "items": items})

    assert response.status_code == 422

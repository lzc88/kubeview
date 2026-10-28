from uuid import uuid4

from sqlalchemy import func, select

from ecommerce.orders.db.models import IdempotencyKey, Order

ITEMS = [
    {"sku": "SKU-1", "qty": 2, "unit_price": "9.50"},
    {"sku": "SKU-2", "qty": 1, "unit_price": "5.00"},
]


def post_order(client, key, user_id="u1", items=ITEMS):
    return client.post(
        "/orders",
        json={"user_id": user_id, "items": items},
        headers={"Idempotency-Key": key},
    )


def order_count(session):
    return session.scalar(select(func.count()).select_from(Order))


def test_missing_key_is_rejected(client, session):
    response = client.post("/orders", json={"user_id": "u1", "items": ITEMS})

    assert response.status_code == 422
    assert order_count(session) == 0


def test_retry_with_same_key_returns_the_original_order(client, session):
    key = str(uuid4())
    first = post_order(client, key)

    retry = post_order(client, key)

    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert order_count(session) == 1


def test_retry_matches_regardless_of_item_order_and_price_format(client, session):
    key = str(uuid4())
    first = post_order(client, key)
    reshuffled = [
        {"sku": "SKU-2", "qty": 1, "unit_price": "5"},
        {"sku": "SKU-1", "qty": 2, "unit_price": "9.5"},
    ]

    retry = post_order(client, key, items=reshuffled)

    assert retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    assert order_count(session) == 1


def test_reused_key_with_different_items_is_rejected(client, session):
    key = str(uuid4())
    post_order(client, key)

    response = post_order(
        client, key, items=[{"sku": "SKU-9", "qty": 1, "unit_price": "1.00"}]
    )

    assert response.status_code == 422
    assert order_count(session) == 1


def test_reused_key_from_another_user_is_rejected(client, session):
    key = str(uuid4())
    post_order(client, key, user_id="u1")

    response = post_order(client, key, user_id="u2")

    assert response.status_code == 422
    assert order_count(session) == 1


def test_different_keys_create_separate_orders(client, session):
    first = post_order(client, str(uuid4()))
    second = post_order(client, str(uuid4()))

    assert first.json()["id"] != second.json()["id"]
    assert order_count(session) == 2


def test_key_is_recorded_against_the_order(client, session):
    key = str(uuid4())
    order = post_order(client, key).json()

    assert session.get(IdempotencyKey, key).order_id == order["id"]

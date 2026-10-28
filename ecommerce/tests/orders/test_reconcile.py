from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, update

from ecommerce.orders import payments_client
from ecommerce.orders.db.models import Order, OrderItem, OrderStatus
from ecommerce.orders.reconcile import reconcile


def add_order(session, status, age=timedelta(0)):
    order = Order(
        user_id="u1",
        total=Decimal("10.00"),
        status=status,
        items=[OrderItem(sku="SKU-1", qty=1, unit_price=Decimal("10.00"))],
    )
    session.add(order)
    session.flush()
    session.execute(
        update(Order)
        .where(Order.id == order.id)
        .values(created_at=func.now() - age, updated_at=func.now() - age)
    )
    session.commit()
    return order


@pytest.fixture
def charge(monkeypatch):
    def set_result(result):
        def fake_charge(order_id, amount):
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(payments_client, "charge", fake_charge)

    return set_result


def status_of(session, order):
    session.refresh(order)
    return order.status


def test_stale_processing_order_is_settled(session, charge):
    charge(True)
    order = add_order(session, OrderStatus.PROCESSING, age=timedelta(minutes=5))

    result = reconcile(session)

    assert result.settled == 1
    assert status_of(session, order) == OrderStatus.PAID


def test_stale_processing_order_can_settle_as_failed(session, charge):
    charge(False)
    order = add_order(session, OrderStatus.PROCESSING, age=timedelta(minutes=5))

    reconcile(session)

    assert status_of(session, order) == OrderStatus.PAYMENT_FAILED


def test_fresh_processing_order_is_left_alone(session, charge):
    charge(True)
    order = add_order(session, OrderStatus.PROCESSING)

    result = reconcile(session)

    assert result.settled == 0
    assert status_of(session, order) == OrderStatus.PROCESSING


def test_processing_order_stays_processing_while_payments_is_down(session, charge):
    charge(payments_client.PaymentsUnavailable("connection refused"))
    order = add_order(session, OrderStatus.PROCESSING, age=timedelta(minutes=5))

    result = reconcile(session)

    assert result.still_processing == 1
    assert status_of(session, order) == OrderStatus.PROCESSING


def test_old_pending_order_is_cancelled(session, charge):
    charge(True)
    order = add_order(session, OrderStatus.PENDING, age=timedelta(hours=1))

    result = reconcile(session)

    assert result.cancelled == 1
    assert status_of(session, order) == OrderStatus.CANCELLED


def test_fresh_pending_order_is_left_alone(session, charge):
    charge(True)
    order = add_order(session, OrderStatus.PENDING)

    reconcile(session)

    assert status_of(session, order) == OrderStatus.PENDING


def test_old_pending_order_is_never_charged(session, monkeypatch):
    def fail_if_called(order_id, amount):
        raise AssertionError("PENDING orders must never be charged")

    monkeypatch.setattr(payments_client, "charge", fail_if_called)
    add_order(session, OrderStatus.PENDING, age=timedelta(hours=1))

    reconcile(session)


def test_settled_orders_are_untouched(session, charge):
    charge(False)
    order = add_order(session, OrderStatus.PAID, age=timedelta(hours=1))

    reconcile(session)

    assert status_of(session, order) == OrderStatus.PAID

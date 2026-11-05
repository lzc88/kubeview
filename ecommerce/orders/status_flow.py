from sqlalchemy import ColumnElement, update
from sqlalchemy.orm import Session

from ecommerce.orders.db.models import Order, OrderStatus, OrderStatusEvent


def transition(
    session: Session,
    from_status: OrderStatus,
    to_status: OrderStatus,
    *where: ColumnElement[bool],
) -> list[int]:

    moved = session.scalars(
        update(Order)
        .where(Order.status == from_status, *where)
        .values(status=to_status)
        .returning(Order.id)
    ).all()

    session.add_all(
        OrderStatusEvent(order_id=order_id, from_status=from_status, to_status=to_status)
        for order_id in moved
    )

    return list(moved)

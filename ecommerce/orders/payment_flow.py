from sqlalchemy import update
from sqlalchemy.orm import Session

from ecommerce.orders import payments_client
from ecommerce.orders.db.models import Order, OrderStatus


def settle(session: Session, order: Order) -> None:
    succeeded = payments_client.charge(order.id, order.total)
    session.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == OrderStatus.PROCESSING)
        .values(status=OrderStatus.PAID if succeeded else OrderStatus.PAYMENT_FAILED)
    )
    session.commit()
    session.refresh(order)

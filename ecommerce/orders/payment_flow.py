from sqlalchemy import update
from sqlalchemy.orm import Session

from ecommerce.orders import payments_client
from ecommerce.orders.db.models import Order, OrderStatus, OrderStatusEvent

ORDER_STATUS_FOR = {
    "SUCCEEDED": OrderStatus.PAID,
    "FAILED": OrderStatus.PAYMENT_FAILED,
}


def settle(session: Session, order: Order) -> payments_client.PaymentResult:

    result = payments_client.charge(order.id, order.total)

    if result.status != "PENDING":
        apply_result(session, order, result.status)

    return result


def apply_result(session: Session, order: Order, payment_status: str) -> None:

    to_status = ORDER_STATUS_FOR[payment_status]

    changed = session.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == OrderStatus.PROCESSING)
        .values(status=to_status)
        .returning(Order.id)
    ).scalar_one_or_none()

    if changed is not None:
        session.add(
            OrderStatusEvent(
                order_id=order.id,
                from_status=OrderStatus.PROCESSING,
                to_status=to_status,
            )
        )

    session.commit()
    session.refresh(order)
    session.expire(order, ["history"])

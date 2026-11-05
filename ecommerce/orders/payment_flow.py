from sqlalchemy.orm import Session

from ecommerce.orders import payments_client, status_flow
from ecommerce.orders.db.models import Order, OrderStatus

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

    status_flow.transition(
        session,
        OrderStatus.PROCESSING,
        ORDER_STATUS_FOR[payment_status],
        Order.id == order.id,
    )

    session.commit()
    session.expire(order)

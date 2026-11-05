from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ecommerce.orders import idempotency, payment_flow, payments_client, status_flow
from ecommerce.orders.db.db import get_session
from ecommerce.orders.db.models import (
    IdempotencyKey,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusEvent,
)
from ecommerce.orders.schemas import (
    OrderCreate,
    OrderPayRead,
    OrderRead,
    PaymentNotification,
)

app = FastAPI(title="orders")

SessionDep = Annotated[Session, Depends(get_session)]

WITH_LINES = [selectinload(Order.items), selectinload(Order.history)]


def load_order(session: Session, order_id: int) -> Order:
    return session.scalars(
        select(Order)
        .where(Order.id == order_id)
        .options(*WITH_LINES)
        .execution_options(populate_existing=True)
    ).one()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    session: SessionDep,
    response: Response,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=255)],
) -> OrderRead:

    request_hash = idempotency.request_hash(payload)

    order = Order(
        user_id=payload.user_id,
        total=sum(item.qty * item.unit_price for item in payload.items),
        items=[OrderItem(**item.model_dump()) for item in payload.items],
        history=[OrderStatusEvent(from_status=None, to_status=OrderStatus.PENDING)],
    )

    session.add(order)
    session.flush()

    if idempotency.claim(session, idempotency_key, request_hash, order.id):
        session.commit()
        return OrderRead.model_validate(order)

    session.rollback()
    existing = session.get(IdempotencyKey, idempotency_key)

    if existing is None or existing.request_hash != request_hash:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Idempotency-Key was already used with a different request",
        )

    response.status_code = status.HTTP_200_OK

    return get_order(existing.order_id, session)


@app.get("/orders/{order_id}")
def get_order(order_id: int, session: SessionDep) -> OrderRead:

    order = session.get(Order, order_id, options=WITH_LINES)

    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")

    return OrderRead.model_validate(order)


@app.post("/orders/{order_id}/pay")
def pay_order(order_id: int, session: SessionDep, response: Response) -> OrderPayRead:

    order = session.get(Order, order_id, with_for_update=True)

    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")

    if order.status not in (OrderStatus.PENDING, OrderStatus.PROCESSING):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"order is {order.status}, not payable"
        )

    if order.status == OrderStatus.PENDING:
        status_flow.transition(
            session, OrderStatus.PENDING, OrderStatus.PROCESSING, Order.id == order.id
        )

    session.commit()

    try:
        result = payment_flow.settle(session, order)
        checkout_url = result.checkout_url

    except payments_client.PaymentsUnavailable:
        checkout_url = None

    order = load_order(session, order_id)

    if order.status == OrderStatus.PROCESSING:
        response.status_code = status.HTTP_202_ACCEPTED

    return OrderPayRead.model_validate(order).model_copy(
        update={"checkout_url": checkout_url}
    )


@app.post("/orders/{order_id}/payment-result")
def record_payment_result(
    order_id: int, payload: PaymentNotification, session: SessionDep
) -> OrderRead:

    order = session.get(Order, order_id)

    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")

    payment_flow.apply_result(session, order, payload.status)

    return OrderRead.model_validate(load_order(session, order_id))


@app.get("/orders")
def list_orders(user_id: str, session: SessionDep) -> list[OrderRead]:

    orders = session.scalars(
        select(Order)
        .where(Order.user_id == user_id)
        .options(*WITH_LINES)
        .order_by(Order.created_at.desc(), Order.id.desc())
    )

    return [OrderRead.model_validate(order) for order in orders]

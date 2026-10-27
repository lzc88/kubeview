from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ecommerce.orders.db.db import get_session
from ecommerce.orders.db.models import Order, OrderItem
from ecommerce.orders.schemas import OrderCreate, OrderRead

app = FastAPI(title="orders")

SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, session: SessionDep) -> OrderRead:
    order = Order(
        user_id=payload.user_id,
        total=sum(item.qty * item.unit_price for item in payload.items),
        items=[OrderItem(**item.model_dump()) for item in payload.items],
    )
    session.add(order)
    session.commit()
    return OrderRead.model_validate(order)


@app.get("/orders/{order_id}")
def get_order(order_id: int, session: SessionDep) -> OrderRead:
    order = session.get(Order, order_id, options=[selectinload(Order.items)])
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "order not found")
    return OrderRead.model_validate(order)


@app.get("/orders")
def list_orders(user_id: str, session: SessionDep) -> list[OrderRead]:
    orders = session.scalars(
        select(Order)
        .where(Order.user_id == user_id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    return [OrderRead.model_validate(order) for order in orders]

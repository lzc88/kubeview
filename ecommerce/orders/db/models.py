import socket
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ecommerce.orders.db.base import Base


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CANCELLED = "CANCELLED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"


class Order(Base):

    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(f"'{s}'" for s in OrderStatus)})",
            name="orders_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    history: Mapped[list["OrderStatusEvent"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="OrderStatusEvent.id",
    )

    def move_to(self, status: OrderStatus) -> None:
        self.history.append(OrderStatusEvent(from_status=self.status, to_status=status))
        self.status = status


class OrderItem(Base):

    __tablename__ = "order_items"

    __table_args__ = (
        UniqueConstraint("order_id", "sku", name="order_items_order_sku_key"),
        CheckConstraint("qty > 0", name="order_items_qty_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    sku: Mapped[str]
    qty: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")


POD = socket.gethostname()


class OrderStatusEvent(Base):

    __tablename__ = "order_status_events"

    __table_args__ = (
        CheckConstraint(
            f"to_status IN ({', '.join(f"'{s}'" for s in OrderStatus)})",
            name="order_status_events_to_status_valid",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[str | None]
    to_status: Mapped[str]
    pod: Mapped[str] = mapped_column(default=lambda: POD)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="history")


class IdempotencyKey(Base):

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(primary_key=True)
    request_hash: Mapped[str]
    order_id: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

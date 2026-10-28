from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from ecommerce.payments.db.base import Base


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Payment(Base):

    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(f"'{s}'" for s in PaymentStatus)})",
            name="payments_status_valid",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[int] = mapped_column(unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(
        default=PaymentStatus.PENDING, server_default=PaymentStatus.PENDING
    )
    provider: Mapped[str]
    provider_payment_id: Mapped[str | None]
    checkout_session_id: Mapped[str | None]
    checkout_url: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

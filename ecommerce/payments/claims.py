from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ecommerce.payments.config import settings
from ecommerce.payments.db.models import Payment, PaymentStatus


def claim(session: Session, order_id: int, amount: Decimal) -> Payment | None:

    payment = session.scalar(
        insert(Payment)
        .values(order_id=order_id, amount=amount, provider="stripe")
        .on_conflict_do_nothing(index_elements=[Payment.order_id])
        .returning(Payment)
    )

    if payment is None:

        stale_cutoff = func.now() - timedelta(
            seconds=settings.pending_retry_after_seconds
        )

        payment = session.scalar(
            update(Payment)
            .where(
                Payment.order_id == order_id,
                Payment.amount == amount,
                Payment.status == PaymentStatus.PENDING,
                Payment.checkout_session_id.is_(None),
                Payment.updated_at < stale_cutoff,
            )
            .values(updated_at=func.now())
            .returning(Payment)
        )

    session.commit()

    return payment

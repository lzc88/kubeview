from dataclasses import dataclass
from datetime import timedelta
from typing import cast

from sqlalchemy import CursorResult, delete, func, select, update
from sqlalchemy.orm import Session

from ecommerce.orders import payments_client
from ecommerce.orders.config import settings
from ecommerce.orders.db.db import SessionLocal
from ecommerce.orders.db.models import IdempotencyKey, Order, OrderStatus
from ecommerce.orders.payment_flow import settle


@dataclass
class ReconcileResult:
    settled: int = 0
    still_processing: int = 0
    cancelled: int = 0
    expired_keys: int = 0


def reconcile(session: Session) -> ReconcileResult:
    result = ReconcileResult()

    processing_cutoff = func.now() - timedelta(
        seconds=settings.reconcile_processing_after_seconds
    )
    stale = session.scalars(
        select(Order).where(
            Order.status == OrderStatus.PROCESSING,
            Order.updated_at < processing_cutoff,
        )
    ).all()
    for order in stale:
        try:
            settle(session, order)
            result.settled += 1
        except payments_client.PaymentsUnavailable:
            result.still_processing += 1

    pending_cutoff = func.now() - timedelta(minutes=settings.pending_order_ttl_minutes)
    cancelled = cast(
        CursorResult,
        session.execute(
            update(Order)
            .where(
                Order.status == OrderStatus.PENDING, Order.created_at < pending_cutoff
            )
            .values(status=OrderStatus.CANCELLED)
        ),
    )
    result.cancelled = cancelled.rowcount

    key_cutoff = func.now() - timedelta(hours=settings.idempotency_key_ttl_hours)
    expired = cast(
        CursorResult,
        session.execute(
            delete(IdempotencyKey).where(IdempotencyKey.created_at < key_cutoff)
        ),
    )
    result.expired_keys = expired.rowcount
    session.commit()

    return result


if __name__ == "__main__":
    with SessionLocal() as session:
        print(reconcile(session))

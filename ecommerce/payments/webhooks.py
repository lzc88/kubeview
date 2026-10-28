import stripe
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ecommerce.payments import providers
from ecommerce.payments.config import settings
from ecommerce.payments.db.models import Payment, PaymentStatus


class InvalidWebhook(Exception):
    pass


def verify(payload: bytes, signature: str) -> stripe.Event:

    if settings.stripe_webhook_secret is None:
        raise InvalidWebhook("STRIPE_WEBHOOK_SECRET is not set")

    try:
        return providers.stripe_client().construct_event(
            payload, signature, settings.stripe_webhook_secret.get_secret_value()
        )

    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise InvalidWebhook(str(exc)) from exc


def outcome(event: stripe.Event) -> PaymentStatus | None:

    match event.type:
        case "checkout.session.completed":
            paid = event.data.object.payment_status == "paid"
            return PaymentStatus.SUCCEEDED if paid else None
        case "checkout.session.async_payment_succeeded":
            return PaymentStatus.SUCCEEDED
        case "checkout.session.async_payment_failed" | "checkout.session.expired":
            return PaymentStatus.FAILED

    return None


def record(session: Session, event: stripe.Event) -> Payment | None:

    status = outcome(event)
    checkout = event.data.object

    if status is None or not checkout.client_reference_id:
        return None

    order_id = int(checkout.client_reference_id)
    intent = checkout.payment_intent

    session.execute(
        update(Payment)
        .where(Payment.order_id == order_id, Payment.status == PaymentStatus.PENDING)
        .values(
            status=status,
            provider_payment_id=intent if isinstance(intent, str) else None,
        )
    )

    session.commit()

    return session.scalars(
        select(Payment).where(Payment.order_id == order_id)
    ).one_or_none()

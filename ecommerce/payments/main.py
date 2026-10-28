from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ecommerce.payments import orders_client, providers, webhooks
from ecommerce.payments.claims import claim
from ecommerce.payments.db.db import get_session
from ecommerce.payments.db.models import Payment, PaymentStatus
from ecommerce.payments.schemas import PaymentCreate, PaymentRead

app = FastAPI(title="payments")

SessionDep = Annotated[Session, Depends(get_session)]


async def raw_body(request: Request) -> bytes:
    return await request.body()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/payments", status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate, session: SessionDep, response: Response
) -> PaymentRead:

    payment = claim(session, payload.order_id, payload.amount)

    if payment is None:

        existing = session.scalars(
            select(Payment).where(Payment.order_id == payload.order_id)
        ).one()

        if existing.amount != payload.amount:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "order already has a payment for a different amount",
            )

        if existing.status == PaymentStatus.PENDING and existing.checkout_url is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "payment for this order is in progress"
            )

        response.status_code = (
            status.HTTP_202_ACCEPTED
            if existing.status == PaymentStatus.PENDING
            else status.HTTP_200_OK
        )

        return PaymentRead.model_validate(existing)

    try:
        result = providers.charge(payment.order_id, payment.amount, payment.created_at)

    except providers.ProviderUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "payment provider unavailable"
        )

    session.execute(
        update(Payment)
        .where(Payment.id == payment.id, Payment.status == PaymentStatus.PENDING)
        .values(
            status=result.status,
            provider_payment_id=result.provider_payment_id,
            checkout_session_id=result.checkout_session_id,
            checkout_url=result.checkout_url,
        )
    )

    session.commit()
    session.refresh(payment)

    if payment.status == PaymentStatus.PENDING:
        response.status_code = status.HTTP_202_ACCEPTED

    return PaymentRead.model_validate(payment)


@app.post("/webhooks/stripe")
def stripe_webhook(
    body: Annotated[bytes, Depends(raw_body)],
    stripe_signature: Annotated[str, Header()],
    session: SessionDep,
) -> dict[str, str]:

    try:
        event = webhooks.verify(body, stripe_signature)

    except webhooks.InvalidWebhook:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid webhook")

    payment = webhooks.record(session, event)

    if payment is not None and payment.status != PaymentStatus.PENDING:
        try:
            orders_client.notify(payment.order_id, payment.status)

        except orders_client.OrdersUnavailable:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "orders service unavailable"
            )

    return {"status": "ok"}

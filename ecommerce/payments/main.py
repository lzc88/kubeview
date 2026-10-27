import random
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Response, status

from ecommerce.payments.config import settings
from ecommerce.payments.schemas import PaymentCreate, PaymentRead, PaymentStatus
from ecommerce.payments.store import AmountMismatch, PaymentInProgress, store

app = FastAPI(title="payments")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/payments", status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate, response: Response) -> PaymentRead:
    try:
        existing = store.reserve(payload.order_id, payload.amount)
    except AmountMismatch:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "order already has a payment for a different amount",
        )
    except PaymentInProgress:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "payment for this order is in progress"
        )
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    time.sleep(settings.latency_ms / 1000)
    succeeded = random.random() >= settings.failure_rate
    payment = PaymentRead(
        payment_id=uuid4(),
        order_id=payload.order_id,
        amount=payload.amount,
        status=PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED,
    )
    store.save(payment)
    return payment

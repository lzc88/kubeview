import random
import time
from uuid import uuid4

from fastapi import FastAPI, status

from ecommerce.payments.config import settings
from ecommerce.payments.schemas import PaymentCreate, PaymentRead, PaymentStatus

app = FastAPI(title="payments")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/payments", status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate) -> PaymentRead:
    time.sleep(settings.latency_ms / 1000)
    succeeded = random.random() >= settings.failure_rate
    return PaymentRead(
        payment_id=uuid4(),
        order_id=payload.order_id,
        amount=payload.amount,
        status=PaymentStatus.SUCCEEDED if succeeded else PaymentStatus.FAILED,
    )

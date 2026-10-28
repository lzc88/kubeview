from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ecommerce.payments.db.models import PaymentStatus


class PaymentCreate(BaseModel):
    order_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: int
    amount: Decimal
    status: PaymentStatus
    provider: str
    provider_payment_id: str | None
    checkout_url: str | None

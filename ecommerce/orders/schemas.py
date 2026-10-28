from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ecommerce.orders.db.models import OrderStatus


class OrderItemCreate(BaseModel):
    sku: str = Field(min_length=1)
    qty: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class OrderCreate(BaseModel):
    user_id: str = Field(min_length=1)
    items: list[OrderItemCreate] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def skus_unique(cls, items: list[OrderItemCreate]) -> list[OrderItemCreate]:
        skus = [item.sku for item in items]
        if len(skus) != len(set(skus)):
            raise ValueError("each sku may appear only once")
        return items


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku: str
    qty: int
    unit_price: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    total: Decimal
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]


class OrderPayRead(OrderRead):
    checkout_url: str | None = None


class PaymentNotification(BaseModel):
    status: Literal["SUCCEEDED", "FAILED"]

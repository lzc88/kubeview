from decimal import Decimal
from threading import Lock

from ecommerce.payments.schemas import PaymentRead


class PaymentInProgress(Exception):
    pass


class AmountMismatch(Exception):
    pass


class PaymentStore:

    def __init__(self) -> None:
        self._lock = Lock()
        self._amounts: dict[int, Decimal] = {}
        self._payments: dict[int, PaymentRead] = {}

    def reserve(self, order_id: int, amount: Decimal) -> PaymentRead | None:
        with self._lock:
            if order_id not in self._amounts:
                self._amounts[order_id] = amount
                return None
            if self._amounts[order_id] != amount:
                raise AmountMismatch
            if order_id not in self._payments:
                raise PaymentInProgress
            return self._payments[order_id]

    def save(self, payment: PaymentRead) -> None:
        with self._lock:
            self._payments[payment.order_id] = payment

    def clear(self) -> None:
        with self._lock:
            self._amounts.clear()
            self._payments.clear()


store = PaymentStore()

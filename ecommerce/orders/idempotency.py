import hashlib
import json

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ecommerce.orders.db.models import IdempotencyKey
from ecommerce.orders.schemas import OrderCreate


def request_hash(payload: OrderCreate) -> str:

    canonical = {
        "user_id": payload.user_id,
        "items": sorted(
            [item.sku, item.qty, f"{item.unit_price:.2f}"] for item in payload.items
        ),
    }

    encoded = json.dumps(canonical, separators=(",", ":")).encode()

    return hashlib.sha256(encoded).hexdigest()


def claim(session: Session, key: str, request_hash: str, order_id: int) -> bool:

    claimed = session.scalar(
        insert(IdempotencyKey)
        .values(key=key, request_hash=request_hash, order_id=order_id)
        .on_conflict_do_nothing(index_elements=[IdempotencyKey.key])
        .returning(IdempotencyKey.key)
    )

    return claimed is not None

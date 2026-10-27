import ecommerce.orders.db.models  # noqa: F401  (importing registers the tables on Base.metadata)
from ecommerce.orders.db.base import Base
from ecommerce.orders.db.db import engine

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("tables:", ", ".join(Base.metadata.tables))

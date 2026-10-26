import ecommerce.db.models  # noqa: F401  (importing registers the tables on Base.metadata)
from ecommerce.db.db import Base, engine

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("tables:", ", ".join(Base.metadata.tables))

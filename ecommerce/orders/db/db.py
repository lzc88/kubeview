from sqlalchemy import Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ecommerce.orders.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    type_annotation_map = {str: Text}


def get_session():
    with SessionLocal() as session:
        yield session

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import inspect, text
from sqlmodel import Field, SQLModel, create_engine, Session

from . import config


class ProductStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    FAILED = "FAILED"


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    niche: str
    title: str
    sku_slug: str = Field(index=True)
    format: str = "printable"
    price: float = 4.99
    status: ProductStatus = Field(default=ProductStatus.DRAFT)
    fail_code: Optional[str] = None
    fail_detail: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Artifact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    type: str
    path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


engine = create_engine(f"sqlite:///{config.DB_PATH}")


def reset_engine() -> None:
    global engine
    engine = create_engine(f"sqlite:///{config.DB_PATH}")


def init_db() -> None:
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _migrate_db()


def _migrate_db() -> None:
    """Migrate existing database schema to match current models."""
    try:
        inspector = inspect(engine)
        
        if "product" in inspector.get_table_names():
            columns = {col["name"] for col in inspector.get_columns("product")}
            
            # Add fail_code column if missing
            if "fail_code" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE product ADD COLUMN fail_code TEXT"))
            
            # Add fail_detail column if missing
            if "fail_detail" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE product ADD COLUMN fail_detail TEXT"))
    except Exception:
        # If migration fails, table might not exist yet or schema is already up to date
        pass


def get_session() -> Session:
    return Session(engine, expire_on_commit=False)

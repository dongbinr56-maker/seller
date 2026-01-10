from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

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


def get_session() -> Session:
    return Session(engine, expire_on_commit=False)

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Iterable, List

from slugify import slugify

from sqlmodel import select

from ..config import ALLOWED_NICHES
from ..models import Product, ProductStatus, get_session, init_db


REQUIRED_COLUMNS = {"niche", "title"}


def load_rows(csv_path: Path) -> List[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing columns: {', '.join(sorted(missing))}")
        rows = [row for row in reader if any(value.strip() for value in row.values())]
    if not rows:
        raise ValueError("CSV has no data rows")
    return rows


def slug_from_title(title: str) -> str:
    slug = slugify(title)
    slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    if not slug:
        slug = hashlib.md5(title.encode("utf-8")).hexdigest()[:12]
    if ".." in slug or "/" in slug or "\\" in slug:
        raise ValueError("Invalid slug generated from title")
    return slug


def ingest_products(csv_path: Path) -> List[Product]:
    init_db()
    rows = load_rows(csv_path)
    seen = set()
    products: List[Product] = []
    for row in rows:
        niche = row["niche"].strip()
        title = row["title"].strip()
        if not niche or not title:
            raise ValueError("CSV rows must include niche and title")
        if niche not in ALLOWED_NICHES:
            raise ValueError(f"Unsupported niche: {niche}")
        key = (niche.lower(), title.lower())
        if key in seen:
            raise ValueError(f"Duplicate title in niche: {niche} - {title}")
        seen.add(key)
        slug = slug_from_title(title)
        products.append(
            Product(
                niche=niche,
                title=title,
                sku_slug=slug,
                status=ProductStatus.DRAFT,
            )
        )
    with get_session() as session:
        session.add_all(products)
        session.commit()
        for product in products:
            session.refresh(product)
    return products


def list_products(statuses: Iterable[ProductStatus], niche: str | None = None) -> List[Product]:
    init_db()
    with get_session() as session:
        statement = select(Product)
        if niche:
            statement = statement.where(Product.niche == niche)
        if statuses:
            statement = statement.where(Product.status.in_(list(statuses)))
        return list(session.exec(statement))

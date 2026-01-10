from __future__ import annotations

import json
import logging
import hashlib
from pathlib import Path
from typing import Iterable, List

from sqlmodel import select
from sqlalchemy.exc import SQLAlchemyError

from .. import config
from ..config import BANNED_WORDS, REQUIRED_MODULES
from ..models import Product, ProductStatus, get_session

logger = logging.getLogger(__name__)

def _contains_banned_words(text: str) -> List[str]:
    lowered = text.lower()
    return [word for word in BANNED_WORDS if word in lowered]


def spec_signature(spec: dict) -> str:
    modules = spec.get("modules", [])
    layout = spec.get("layout") or {}
    if not isinstance(layout, dict):
        layout = {}
    return "|".join(
        [
            f"niche={spec.get('niche')}",
            "modules=" + ",".join(modules),
            f"pages={layout.get('page_count')}",
            f"grid={layout.get('grid_variant')}",
        ]
    )


def signature_hash(signature: str) -> str:
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)


SIMILARITY_THRESHOLD = 0.95


def build_signature_index() -> list[dict]:
    try:
        with get_session() as session:
            ready_slugs = set(
                session.exec(select(Product.sku_slug).where(Product.status == ProductStatus.READY)).all()
            )
    except SQLAlchemyError:
        return []
    if not ready_slugs:
        return []
    entries: list[dict] = []
    for spec_path in Path(config.OUT_DIR).glob("*/spec.json"):
        slug = spec_path.parent.name
        if slug not in ready_slugs:
            continue
        try:
            existing = json.loads(spec_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            continue
        signature = spec_signature(existing)
        entries.append(
            {
                "slug": slug,
                "niche": existing.get("niche"),
                "modules": existing.get("modules", []),
                "signature": signature,
                "hash": signature_hash(signature),
            }
        )
    return entries


def check_duplicate_signature(spec: dict, signature_index: list[dict] | None = None) -> str | None:
    current_niche = spec.get("niche")
    current_modules = spec.get("modules", [])
    current_slug = spec.get("slug")
    if not current_slug:
        return None
    entries = signature_index or build_signature_index()
    if not entries:
        return None
    current_signature = spec_signature(spec)
    current_hash = signature_hash(current_signature)
    for entry in entries:
        if entry["hash"] == current_hash:
            logger.info("Duplicate signature match for %s vs %s", current_slug, entry["slug"])
            return f"Spec duplicate of {entry['slug']}"
    for entry in entries:
        if entry["niche"] != current_niche:
            continue
        similarity = jaccard_similarity(current_modules, entry.get("modules", []))
        if similarity > SIMILARITY_THRESHOLD:
            logger.info(
                "Spec similarity %.2f for %s vs %s",
                similarity,
                current_slug,
                entry["slug"],
            )
            return f"Spec too similar to {entry['slug']}"
    return None


def validate_spec(spec: dict, metadata: dict) -> List[str]:
    errors: List[str] = []
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    text_fields = [spec.get("title", ""), description] + spec.get("modules", []) + tags
    for text in text_fields:
        banned = _contains_banned_words(text)
        if banned:
            errors.append(f"Banned words found: {', '.join(banned)}")
            break
    missing = [module for module in REQUIRED_MODULES if module not in spec.get("modules", [])]
    if missing:
        errors.append(f"Missing required modules: {', '.join(missing)}")
    if not (200 <= len(description) <= 400):
        errors.append("Description length must be between 200 and 400 characters")
    duplicate = check_duplicate_signature(spec, signature_index=metadata.get("signature_index"))
    if duplicate:
        errors.append(duplicate)
    return errors

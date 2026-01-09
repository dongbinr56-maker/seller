from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from sqlmodel import select

from ..config import BANNED_WORDS, REQUIRED_MODULES
from ..models import Product, ProductStatus, get_session
from ..storage import artifact_path


def _contains_banned_words(text: str) -> List[str]:
    lowered = text.lower()
    return [word for word in BANNED_WORDS if word in lowered]


def spec_signature(spec: dict) -> str:
    modules = spec.get("modules", [])
    layout = spec.get("layout") or {}
    if not isinstance(layout, dict):
        layout = {}
    return "|".join(modules) + f"|grid={layout.get('grid_variant')}|pages={layout.get('page_count')}"


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)


SIMILARITY_THRESHOLD = 0.95


def check_duplicate_signature(spec: dict) -> str | None:
    current_niche = spec.get("niche")
    current_modules = spec.get("modules", [])
    current_slug = spec.get("slug")
    if not current_slug:
        return None
    with get_session() as session:
        ready_slugs = set(
            session.exec(select(Product.sku_slug).where(Product.status == ProductStatus.READY)).all()
        )
    if not ready_slugs:
        return None
    for spec_path in Path(artifact_path(current_slug, "spec")).parent.parent.glob("*/spec.json"):
        if spec_path.parent.name == current_slug:
            continue
        if spec_path.parent.name not in ready_slugs:
            continue
        try:
            existing = json.loads(spec_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            continue
        existing_modules = existing.get("modules", [])
        if existing.get("niche") != current_niche:
            continue
        if jaccard_similarity(current_modules, existing_modules) > SIMILARITY_THRESHOLD:
            return f"Spec too similar to {spec_path.parent.name}"
    return None


def validate_spec(spec: dict, description: str) -> List[str]:
    errors: List[str] = []
    text_fields = [spec.get("title", "")] + spec.get("modules", [])
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
    duplicate = check_duplicate_signature(spec)
    if duplicate:
        errors.append(duplicate)
    return errors

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from ..config import BANNED_WORDS, REQUIRED_MODULES
from ..storage import artifact_path


def _contains_banned_words(text: str) -> List[str]:
    lowered = text.lower()
    return [word for word in BANNED_WORDS if word in lowered]


def spec_signature(modules: Iterable[str]) -> str:
    return "|".join(modules)


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)


def check_duplicate_signature(slug: str, modules: List[str]) -> str | None:
    signature = spec_signature(modules)
    for spec_path in Path(artifact_path(slug, "spec")).parent.parent.glob("*/spec.json"):
        if spec_path.parent.name == slug:
            continue
        existing = json.loads(spec_path.read_text(encoding="utf-8"))
        existing_modules = existing.get("modules", [])
        existing_sig = spec_signature(existing_modules)
        if existing_sig == signature:
            return f"Duplicate spec signature with {spec_path.parent.name}"
        if jaccard_similarity(modules, existing_modules) > 0.8:
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
    duplicate = check_duplicate_signature(spec["slug"], spec.get("modules", []))
    if duplicate:
        errors.append(duplicate)
    return errors

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List

from ..storage import artifact_path


OPTIONAL_MODULES = [
    "habit_grid",
    "reflection",
    "monthly_overview",
    "goal_setting",
    "mood_checkin",
    "priority_matrix",
    "gratitude_log",
    "weekly_review",
    "daily_focus",
    "weekly_planner",
    "meal_planner",
    "water_intake",
    "sleep_log",
    "affirmations",
    "project_steps",
]


def _hash_seed(slug: str, variant: int) -> int:
    seed_input = f"{slug}-{variant}"
    return int(hashlib.md5(seed_input.encode("utf-8")).hexdigest(), 16)


def _select_optional_modules(slug: str, variant: int) -> List[str]:
    seed = _hash_seed(slug, variant)
    count = min(1 + (seed % 4), len(OPTIONAL_MODULES))
    ordered = sorted(
        OPTIONAL_MODULES,
        key=lambda name: hashlib.md5(f"{slug}-{variant}-{name}".encode("utf-8")).hexdigest(),
    )
    return ordered[:count]


def _rotate_modules(modules: List[str], rotation: int) -> List[str]:
    if not modules:
        return modules
    rotation = rotation % len(modules)
    return modules[rotation:] + modules[:rotation]


def build_spec(niche: str, title: str, slug: str, variant: int = 0) -> dict:
    base_modules = ["cover", "how_to", "tracker", "notes"]
    optional = _select_optional_modules(slug, variant)
    modules = base_modules + optional
    seed = _hash_seed(slug, variant)
    modules = _rotate_modules(modules, seed % len(modules))
    if variant % 2 == 1:
        modules = [modules[0]] + list(reversed(modules[1:]))
    return {
        "niche": niche,
        "title": title,
        "slug": slug,
        "modules": modules,
        "layout": {
            "page_count": 3 + (seed % 3),
            "grid_variant": (seed + variant) % 6,
        },
    }


def write_spec(spec: dict) -> Path:
    path = artifact_path(spec["slug"], "spec")
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path

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
]


def _hash_seed(slug: str) -> int:
    return int(hashlib.md5(slug.encode("utf-8")).hexdigest(), 16)


def _select_optional_modules(slug: str) -> List[str]:
    seed = _hash_seed(slug)
    count = 1 if seed % 2 == 0 else 2
    ordered = sorted(OPTIONAL_MODULES, key=lambda name: hashlib.md5(f"{slug}-{name}".encode("utf-8")).hexdigest())
    return ordered[:count]


def build_spec(niche: str, title: str, slug: str) -> dict:
    base_modules = ["cover", "how_to", "tracker", "notes"]
    optional = _select_optional_modules(slug)
    modules = base_modules + optional
    seed = _hash_seed(slug)
    if seed % 3 == 0:
        modules = modules[:2] + modules[3:] + [modules[2]]
    elif seed % 3 == 1:
        modules = [modules[0]] + modules[2:] + [modules[1]]
    return {
        "niche": niche,
        "title": title,
        "slug": slug,
        "modules": modules,
        "layout": {
            "page_count": 3,
            "grid_variant": seed % 4,
        },
    }


def write_spec(spec: dict) -> Path:
    path = artifact_path(spec["slug"], "spec")
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path

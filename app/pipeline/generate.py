from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

from .archetypes import Archetype, pick_archetype, pick_theme
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

# “스펙 메타”에만 들어가는 옵션 모듈(=제품 설명/태그/차별점에 활용)
# 주의: renderer가 이걸 그대로 렌더링하지 않아도 됨(=문서 구조는 recipe가 결정)
OPTIONAL_MODULES_BY_NICHE: Dict[str, List[str]] = {
    "BUDGET": [
        "monthly_overview",
        "goal_setting",
        "priority_matrix",
        "weekly_review",
        "gratitude_log",
        "reflection",
        "project_steps",
    ],
    "ADHD": [
        "daily_focus",
        "weekly_planner",
        "habit_grid",
        "mood_checkin",
        "reflection",
        "affirmations",
        "project_steps",
    ],
}

def _hash_seed(slug: str, variant: int) -> int:
    seed_input = f"{slug}-{variant}"
    return int(hashlib.md5(seed_input.encode("utf-8")).hexdigest(), 16)

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
        "niche": n,
        "title": t,
        "slug": s,
        "variant": int(variant),
        "theme": theme,
        "archetype": archetype.key,
        "modules": modules,
        # renderer가 이걸 기반으로 “진짜 다른 PDF”를 찍도록 강제하는 핵심 필드
        "recipe": recipe,
        "copy": {
            "cover_subtitle": archetype.cover_subtitle,
            "included_lines": list(archetype.included_lines),
            "howto_lines": list(archetype.howto_lines),
        },
        "layout": {
            "page_count": 3 + (seed % 3),
            "grid_variant": (seed + variant) % 6,
        },
    }


def write_spec(
    spec: dict,
    base_dir: Path | None = None,
    include_slug: bool = True,
) -> Path:
    path = artifact_path(spec["slug"], "spec", base_dir=base_dir, include_slug=include_slug)
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path

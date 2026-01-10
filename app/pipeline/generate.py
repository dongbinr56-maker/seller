from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

from .archetypes import Archetype, pick_archetype, pick_theme
from ..storage import artifact_path


REQUIRED_MODULES: List[str] = ["cover", "how_to", "tracker", "notes"]

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

DEFAULT_PRINT_TIPS: List[str] = [
    "Use Actual Size or 100% scale for best results",
    "Try thicker paper for trackers you reuse often",
    "Print only the pages you need each week",
    "Keep one master copy and make clean reprints",
]


def _hash_seed(slug: str, variant: int) -> int:
    seed_input = f"{slug}-{variant}"
    return int(hashlib.md5(seed_input.encode("utf-8")).hexdigest(), 16)


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _select_optional_modules(slug: str, niche: str, variant: int) -> List[str]:
    n = (niche or "").strip().upper()
    pool = OPTIONAL_MODULES_BY_NICHE.get(n, [])
    if not pool:
        return []

    seed = _hash_seed(slug, variant)
    count = 2 + (seed % 3)  # 2~4
    count = min(count, len(pool))

    ordered = sorted(
        pool,
        key=lambda name: hashlib.md5(f"{slug}-{variant}-{name}".encode("utf-8")).hexdigest(),
    )
    return ordered[:count]


def _normalize_preview_pages(pages: List[int], page_count: int) -> List[int]:
    if page_count <= 0:
        return [0, 0, 0]

    out: List[int] = []
    seen = set()
    for p in pages:
        pp = int(min(max(int(p), 0), page_count - 1))
        if pp in seen:
            continue
        seen.add(pp)
        out.append(pp)
        if len(out) == 3:
            break

    # 부족하면 앞에서부터 채움
    i = 0
    while len(out) < 3:
        cand = min(i, page_count - 1)
        if cand not in seen:
            seen.add(cand)
            out.append(cand)
        i += 1

    return out[:3]


def build_spec(niche: str, title: str, slug: str, variant: int = 0) -> dict:
    n = (niche or "").strip().upper()
    t = (title or "").strip()
    s = (slug or "").strip()

    seed = _hash_seed(s, variant)

    archetype: Archetype = pick_archetype(slug=s, niche=n, title=t)
    theme = pick_theme(f"{s}-{variant}")

    recipe = list(archetype.recipe)
    page_count = len(recipe)

    preview_pages = _normalize_preview_pages(list(archetype.preview_pages), page_count)

    optional = _select_optional_modules(slug=s, niche=n, variant=variant)

    modules = _dedupe_preserve_order(
        REQUIRED_MODULES
        + recipe
        + optional
    )

    grid_variant = (seed + variant) % 6

    return {
        "niche": n,
        "title": t,
        "slug": s,
        "variant": int(variant),
        "theme": theme,
        "archetype": archetype.key,
        "modules": modules,
        "recipe": recipe,
        "copy": {
            "cover_subtitle": archetype.cover_subtitle,
            "included_lines": list(archetype.included_lines),
            "howto_lines": list(archetype.howto_lines),
            "print_tips": list(DEFAULT_PRINT_TIPS),
        },
        "layout": {
            "page_count": int(page_count),
            "grid_variant": int(grid_variant),
            "preview_pages": preview_pages,
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

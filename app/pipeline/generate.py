from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

from .archetypes import Archetype, pick_archetype, pick_theme
from ..storage import artifact_path


# 기존 파이프라인/QA에서 "필수 모듈"로 기대할 가능성이 높은 항목은 유지.
# (render_pdf는 recipe를 보게 만들고, modules는 메타/QA 용도로 남겨두는 전략)
REQUIRED_MODULES: List[str] = ["cover", "how_to", "tracker", "notes"]

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

    # 2~4개 정도로 분산 (너가 “복붙 느낌 줄여라”라 했으니 조금 더 공격적으로 다양화)
    count = 2 + (seed % 3)  # 2,3,4
    count = min(count, len(pool))

    ordered = sorted(
        pool,
        key=lambda name: hashlib.md5(f"{slug}-{variant}-{name}".encode("utf-8")).hexdigest(),
    )
    return ordered[:count]


def build_spec(niche: str, title: str, slug: str, variant: int = 0) -> dict:
    """
    스펙 생성의 핵심 결정:
    1) archetype = 페이지 구성(recipe) + 카피 세트(부제/포함/사용법)
    2) theme = 색/룩앤필 프리셋
    3) modules = QA/메타용(기존 required 유지 + recipe 포함 + 옵션 일부)
    4) layout.page_count = recipe 길이 기반(=실제 PDF 페이지 수와 일치하도록)
    """
    n = (niche or "").strip().upper()
    t = (title or "").strip()
    s = (slug or "").strip()

    seed = _hash_seed(s, variant)

    archetype: Archetype = pick_archetype(slug=s, niche=n, title=t)

    # theme도 variant까지 섞어서 같은 slug라도 변주 가능하게(추후 SKU 변형/리메이크에 유리)
    theme = pick_theme(f"{s}-{variant}")

    recipe = list(archetype.recipe)
    page_count = len(recipe)

    # preview 페이지는 archetype에서 지정한 걸 우선 사용하되,
    # page_count보다 큰 인덱스가 나오지 않게 방어.
    preview_pages = []
    for p in archetype.preview_pages:
        if page_count <= 0:
            continue
        preview_pages.append(int(min(max(p, 0), page_count - 1)))

    # 기존 QA가 REQUIRED_MODULES를 기대할 가능성이 높아서 유지.
    # 다만 “실제 제품 구성”을 더 잘 설명하도록 recipe도 포함시키고, optional도 소량 포함.
    optional = _select_optional_modules(slug=s, niche=n, variant=variant)

    modules = _dedupe_preserve_order(
        REQUIRED_MODULES
        + recipe  # 실제 렌더 구성(페이지 id)도 함께 담아둠(메타/태깅/설명에 활용)
        + optional
    )

    # grid_variant는 renderer에서 테이블/레이아웃 세부 변형에 활용 가능 (0~5)
    grid_variant = (seed + variant) % 6

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
            "page_count": int(page_count),
            "grid_variant": int(grid_variant),
            "preview_pages": preview_pages,
        },
    }


def write_spec(spec: dict) -> Path:
    path = artifact_path(spec["slug"], "spec")
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path

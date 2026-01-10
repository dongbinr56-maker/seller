from __future__ import annotations

from app.pipeline.ingest import slug_from_title


def test_slug_sanitization() -> None:
    slug = slug_from_title("Budget / Planner: 2025!")
    assert slug == "budget-planner-2025"

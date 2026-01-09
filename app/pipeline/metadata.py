from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ..storage import artifact_path


def _base_tags(niche: str) -> List[str]:
    niche_token = niche.lower().replace(" ", "-")
    tags = [
        niche_token,
        f"{niche_token}-planner",
        "printable",
        "pdf",
        "planner",
        "tracker",
        "worksheet",
        "a4",
        "us-letter",
        "instant-download",
        "digital",
        "minimalist",
        "productivity",
        "organization",
        "daily",
        "weekly",
    ]
    unique: List[str] = []
    for tag in tags:
        if tag not in unique:
            unique.append(tag)
    return unique[:13]


def _normalize_description(text: str) -> str:
    if len(text) < 200:
        filler = " Designed for easy printing and daily use, this template keeps your routine consistent and clear."
        max_iterations = 10
        iteration = 0
        while len(text) + len(filler) <= 400 and len(text) < 200 and iteration < max_iterations:
            text += filler
            iteration += 1
    if len(text) > 400:
        text = text[:397].rstrip() + "..."
    if len(text) < 200:
        text = text.ljust(200, " ")
    return text


def build_metadata(niche: str, title: str, slug: str) -> dict:
    seo_title = f"{niche} {title} Printable PDF"
    description = (
        f"Stay organized with the {title} printable designed for {niche} routines. "
        "Includes structured pages, clear trackers, and space to reflect so you can plan consistently. "
        "Print at home in A4 or US Letter and reuse as needed."
    )
    description = _normalize_description(description)
    metadata = {
        "slug": slug,
        "title": seo_title,
        "description": description,
        "tags": _base_tags(niche),
        "price": 4.99,
        "niche": niche,
    }
    return metadata


def write_metadata(metadata: dict) -> Path:
    path = artifact_path(metadata.get("slug", ""), "metadata") if metadata.get("slug") else None
    if path is None:
        raise ValueError("Metadata must include slug for output")
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return path

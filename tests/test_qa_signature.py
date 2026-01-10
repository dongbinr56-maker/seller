from __future__ import annotations

from app.pipeline.qa import check_duplicate_signature, signature_hash, spec_signature


def test_signature_duplicate_detection() -> None:
    existing = {
        "niche": "BUDGET",
        "slug": "alpha",
        "modules": ["cover", "how_to", "tracker", "notes"],
        "layout": {"page_count": 3, "grid_variant": 1},
    }
    signature = spec_signature(existing)
    index = [
        {
            "slug": "alpha",
            "niche": "BUDGET",
            "modules": existing["modules"],
            "signature": signature,
            "hash": signature_hash(signature),
        }
    ]
    candidate = {
        "niche": "BUDGET",
        "slug": "beta",
        "modules": ["cover", "how_to", "tracker", "notes"],
        "layout": {"page_count": 3, "grid_variant": 1},
    }
    assert check_duplicate_signature(candidate, signature_index=index) == "Spec duplicate of alpha"

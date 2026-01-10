from __future__ import annotations

from pathlib import Path
from typing import Iterable

from . import config
from .models import Artifact, Product, get_session


ARTIFACT_NAMES = {
    "pdf_a4": "a4.pdf",
    "pdf_usletter": "letter.pdf",
    "preview_1": "preview_1.png",
    "preview_2": "preview_2.png",
    "preview_3": "preview_3.png",
    "bundle": "bundle.zip",
    "metadata": "metadata.json",
    "spec": "spec.json",
    "error": "error.log",
    "readme": "README.txt",
}


def product_dir(slug: str, base_dir: Path | None = None, include_slug: bool = True) -> Path:
    root = base_dir or config.OUT_DIR
    path = root / slug if include_slug else root
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifact_path(
    slug: str,
    artifact_type: str,
    base_dir: Path | None = None,
    include_slug: bool = True,
) -> Path:
    filename = ARTIFACT_NAMES[artifact_type]
    return product_dir(slug, base_dir=base_dir, include_slug=include_slug) / filename


def record_artifacts(product: Product, artifacts: Iterable[tuple[str, Path]]) -> None:
    with get_session() as session:
        for artifact_type, path in artifacts:
            session.add(
                Artifact(
                    product_id=product.id,
                    type=artifact_type,
                    path=str(path.relative_to(config.OUT_DIR)),
                )
            )
        session.commit()

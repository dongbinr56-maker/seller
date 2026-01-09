from __future__ import annotations

from pathlib import Path
from typing import Iterable

from . import config
from .models import Artifact, Product, get_session


ARTIFACT_NAMES = {
    "pdf_a4": "product_a4.pdf",
    "pdf_usletter": "product_usletter.pdf",
    "preview_1": "preview_1.png",
    "preview_2": "preview_2.png",
    "preview_3": "preview_3.png",
    "bundle": "bundle.zip",
    "metadata": "metadata.json",
    "spec": "spec.json",
    "error": "error.log",
    "readme": "README.txt",
}


def product_dir(slug: str) -> Path:
    path = config.OUT_DIR / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifact_path(slug: str, artifact_type: str) -> Path:
    filename = ARTIFACT_NAMES[artifact_type]
    return product_dir(slug) / filename


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

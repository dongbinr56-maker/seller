from __future__ import annotations

from pathlib import Path
from typing import Iterable, List
import json

from ..models import Product, ProductStatus, get_session, init_db
from ..storage import artifact_path, record_artifacts
from .generate import build_spec, write_spec
from .metadata import build_metadata
from .package import create_bundle, create_readme
from .qa import validate_spec
from .render_pdf import render_pdfs
from .render_preview import render_previews


def _write_error(slug: str, message: str) -> None:
    error_path = artifact_path(slug, "error")
    error_path.write_text(message, encoding="utf-8")


def process_product(product: Product) -> tuple[ProductStatus, List[tuple[str, Path]], List[str]]:
    artifacts: List[tuple[str, Path]] = []
    errors: List[str] = []
    spec = build_spec(product.niche, product.title, product.sku_slug)
    spec_path = write_spec(spec)
    artifacts.append(("spec", spec_path))

    metadata = build_metadata(product.niche, product.title, product.sku_slug)
    errors.extend(validate_spec(spec, metadata["description"]))
    if errors:
        return ProductStatus.FAILED, artifacts, errors

    pdf_a4, pdf_us = render_pdfs(spec)
    artifacts.extend([("pdf_a4", pdf_a4), ("pdf_usletter", pdf_us)])

    previews = render_previews(product.sku_slug, pdf_a4)
    artifacts.extend(
        [
            ("preview_1", previews[0]),
            ("preview_2", previews[1]),
            ("preview_3", previews[2]),
        ]
    )

    metadata_path = artifact_path(product.sku_slug, "metadata")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    artifacts.append(("metadata", metadata_path))

    readme_path = create_readme(product.sku_slug)
    bundle_path = create_bundle(product.sku_slug, pdf_a4, pdf_us, readme_path)
    artifacts.append(("readme", readme_path))
    artifacts.append(("bundle", bundle_path))
    return ProductStatus.READY, artifacts, []


def run_pipeline(products: Iterable[Product]) -> dict:
    init_db()
    results = {"READY": [], "FAILED": []}  # list[str]
    with get_session() as session:
        for product in products:
            try:
                status, artifacts, errors = process_product(product)
            except Exception as exc:
                status = ProductStatus.FAILED
                artifacts = []
                errors = [str(exc)]

            product.status = status
            session.add(product)
            session.commit()
            session.refresh(product)

            if status == ProductStatus.READY:
                record_artifacts(product, artifacts)
                results["READY"].append(product.sku_slug)   # ✅ slug만 저장
            else:
                message = "\n".join(errors) if errors else "Unknown error"
                _write_error(product.sku_slug, message)
                results["FAILED"].append(product.sku_slug) # ✅ slug만 저장
    return results

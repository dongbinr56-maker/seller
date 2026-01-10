from __future__ import annotations

from pathlib import Path
import logging
import shutil
from typing import Iterable, List
import json

from .. import config
from ..models import Product, ProductStatus, get_session, init_db
from ..storage import artifact_path, record_artifacts
from .generate import build_spec, write_spec
from .metadata import build_metadata
from .package import create_bundle, create_readme
from .qa import build_signature_index, signature_hash, spec_signature, validate_spec
from .render_pdf import render_pdfs
from .render_preview import render_previews


MAX_VARIANTS = 10
logger = logging.getLogger(__name__)


def _write_error(slug: str, message: str) -> None:
    error_path = artifact_path(slug, "error", base_dir=config.OUT_DIR)
    error_path.write_text(message, encoding="utf-8")

def _prepare_temp_dir(slug: str) -> Path:
    temp_dir = config.OUT_DIR / f"{slug}.tmp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _finalize_artifacts(
    temp_dir: Path,
    final_dir: Path,
    artifacts: List[tuple[str, Path]],
) -> List[tuple[str, Path]]:
    if final_dir.exists():
        shutil.rmtree(final_dir)
    temp_dir.replace(final_dir)
    finalized: List[tuple[str, Path]] = []
    for artifact_type, path in artifacts:
        finalized.append((artifact_type, final_dir / path.relative_to(temp_dir)))
    return finalized


def process_product(
    product: Product,
    signature_index: list[dict],
) -> tuple[ProductStatus, List[tuple[str, Path]], List[str], dict | None]:
    artifacts: List[tuple[str, Path]] = []
    metadata = build_metadata(product.niche, product.title, product.sku_slug)
    metadata_for_validation = {**metadata, "signature_index": signature_index}
    last_errors: List[str] = []
    spec: dict | None = None
    spec_path: Path | None = None
    temp_dir = _prepare_temp_dir(product.sku_slug)
    for variant in range(MAX_VARIANTS):
        spec = build_spec(product.niche, product.title, product.sku_slug, variant=variant)
        spec_path = write_spec(spec, base_dir=temp_dir, include_slug=False)
        last_errors = validate_spec(spec, metadata_for_validation)
        if not last_errors:
            artifacts.append(("spec", spec_path))
            break
    if last_errors:
        attempts = MAX_VARIANTS
        last_modules = ", ".join(spec["modules"]) if spec else ""
        last_errors = last_errors + [f"Variants tried: {attempts}", f"Last modules: {last_modules}"]
        if spec_path is not None:
            artifacts.append(("spec", spec_path))
        shutil.rmtree(temp_dir, ignore_errors=True)
        return ProductStatus.FAILED, artifacts, last_errors, None

    pdf_a4, pdf_us = render_pdfs(spec, base_dir=temp_dir, include_slug=False)
    artifacts.extend([("pdf_a4", pdf_a4), ("pdf_usletter", pdf_us)])

    previews = render_previews(product.sku_slug, pdf_a4, base_dir=temp_dir, include_slug=False)
    artifacts.extend(
        [
            ("preview_1", previews[0]),
            ("preview_2", previews[1]),
            ("preview_3", previews[2]),
        ]
    )

    metadata_path = artifact_path(product.sku_slug, "metadata", base_dir=temp_dir, include_slug=False)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    artifacts.append(("metadata", metadata_path))

    readme_path = create_readme(product.sku_slug, base_dir=temp_dir, include_slug=False)
    bundle_path = create_bundle(
        product.sku_slug,
        pdf_a4,
        pdf_us,
        readme_path,
        base_dir=temp_dir,
        include_slug=False,
    )
    artifacts.append(("readme", readme_path))
    artifacts.append(("bundle", bundle_path))
    final_dir = config.OUT_DIR / product.sku_slug
    artifacts = _finalize_artifacts(temp_dir, final_dir, artifacts)
    return ProductStatus.READY, artifacts, [], spec


def run_pipeline(products: Iterable[Product]) -> dict[str, list[str]]:
    init_db()
    results: dict[str, list[str]] = {"READY": [], "FAILED": []}
    signature_index = build_signature_index()
    with get_session() as session:
        for product in products:
            try:
                status, artifacts, errors, spec = process_product(product, signature_index)
            except Exception as exc:
                logger.exception("Pipeline error for %s", product.sku_slug)
                status = ProductStatus.FAILED
                artifacts = []
                errors = [str(exc)]
                spec = None

            product.status = status
            if status == ProductStatus.FAILED:
                product.fail_code = "VALIDATION_FAILED" if errors else "PIPELINE_ERROR"
                product.fail_detail = errors[0] if errors else "Unknown error"
            else:
                product.fail_code = None
                product.fail_detail = None
            session.add(product)
            session.commit()
            session.refresh(product)

            if status == ProductStatus.READY:
                if spec is not None:
                    signature = spec_signature(spec)
                    signature_index.append(
                        {
                            "slug": product.sku_slug,
                            "niche": spec.get("niche"),
                            "modules": spec.get("modules", []),
                            "signature": signature,
                            "hash": signature_hash(signature),
                        }
                    )
                record_artifacts(product, artifacts)
                results["READY"].append(product.sku_slug)   # ✅ slug만 저장
            else:
                message = "\n".join(errors) if errors else "Unknown error"
                _write_error(product.sku_slug, message)
                results["FAILED"].append(product.sku_slug) # ✅ slug만 저장
    return results

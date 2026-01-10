from __future__ import annotations

from pathlib import Path
import zipfile

from ..config import DISCLAIMER_TEXT
from ..storage import artifact_path


def create_readme(slug: str) -> Path:
    path = artifact_path(slug, "readme")
    lines = [
        "Thank you for downloading your printable template.",
        "1. Print the PDF pages you need.",
        "2. Use pens or markers to fill in the sections.",
        "3. Store pages in a binder for reuse.",
        "4. Review weekly for progress.",
        f"Disclaimer: {DISCLAIMER_TEXT}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def create_bundle(slug: str, pdf_a4: Path, pdf_us: Path, readme_path: Path) -> Path:
    """
    Create a distributable bundle zip for one SKU.

    Expected contents (all required):
      - product_a4.pdf
      - product_usletter.pdf
      - preview_1.png, preview_2.png, preview_3.png
      - spec.json
      - metadata.json
      - README.txt (or whatever readme_path.name is)
    """
    bundle_path = artifact_path(slug, "bundle")

    # All artifacts live in the same SKU directory as bundle.zip
    sku_dir = bundle_path.parent

    # NOTE: We intentionally resolve by filename here because:
    # - previews/spec/metadata are already generated into out/{slug}/
    # - it avoids guessing artifact_path keys (robust even if keys differ)
    required_files = [
        pdf_a4,
        pdf_us,
        readme_path,
        sku_dir / "preview_1.png",
        sku_dir / "preview_2.png",
        sku_dir / "preview_3.png",
        sku_dir / "spec.json",
        sku_dir / "metadata.json",
    ]

    # Fail fast if any required artifact is missing
    missing = [p for p in required_files if not p.exists()]
    if missing:
        missing_list = ", ".join(str(p) for p in missing)
        raise FileNotFoundError(f"[{slug}] bundle inputs missing: {missing_list}")

    # Deterministic order in the zip (important for reproducibility)
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for p in required_files:
            # Store only the basename in the zip (no folder paths)
            bundle.write(p, arcname=p.name)

    return bundle_path

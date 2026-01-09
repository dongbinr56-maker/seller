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
    bundle_path = artifact_path(slug, "bundle")
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(pdf_a4, pdf_a4.name)
        bundle.write(pdf_us, pdf_us.name)
        bundle.write(readme_path, readme_path.name)
    return bundle_path

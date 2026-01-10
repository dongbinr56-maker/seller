from __future__ import annotations

from pathlib import Path
import zipfile

from ..config import DISCLAIMER_TEXT
from ..storage import artifact_path


def create_readme(
    slug: str,
    base_dir: Path | None = None,
    include_slug: bool = True,
) -> Path:
    path = artifact_path(slug, "readme", base_dir=base_dir, include_slug=include_slug)
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


def create_bundle(
    slug: str,
    pdf_a4: Path,
    pdf_us: Path,
    readme_path: Path,
    base_dir: Path | None = None,
    include_slug: bool = True,
) -> Path:
    bundle_path = artifact_path(slug, "bundle", base_dir=base_dir, include_slug=include_slug)
    fixed_time = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in (pdf_a4, pdf_us, readme_path):
            info = zipfile.ZipInfo(path.name)
            info.date_time = fixed_time
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, path.read_bytes())
    return bundle_path

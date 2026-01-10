from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF

from ..storage import artifact_path


def render_previews(
    slug: str,
    pdf_path: Path,
    base_dir: Path | None = None,
    include_slug: bool = True,
) -> List[Path]:
    outputs: List[Path] = []
    with fitz.open(str(pdf_path)) as doc:
        if doc.page_count < 3:
            raise ValueError("PDF must have at least 3 pages for previews")
        for index in range(3):
            page = doc.load_page(index)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            output_path = artifact_path(
                slug,
                f"preview_{index + 1}",
                base_dir=base_dir,
                include_slug=include_slug,
            )
            pix.save(str(output_path))
            outputs.append(output_path)
    return outputs

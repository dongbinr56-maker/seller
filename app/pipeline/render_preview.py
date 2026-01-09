from __future__ import annotations

from pathlib import Path
from typing import List

import fitz

from ..storage import artifact_path


def render_previews(slug: str, pdf_path: Path) -> List[Path]:
    doc = fitz.open(str(pdf_path))
    if doc.page_count < 3:
        raise ValueError("PDF must have at least 3 pages for previews")
    outputs: List[Path] = []
    for index in range(3):
        page = doc.load_page(index)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        output_path = artifact_path(slug, f"preview_{index + 1}")
        pix.save(str(output_path))
        outputs.append(output_path)
    doc.close()
    return outputs

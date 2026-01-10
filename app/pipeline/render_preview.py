from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF

from ..storage import artifact_path


def _pick_preview_pages(spec: dict) -> Tuple[int, int, int]:
    # generate 단계에서 넣은 preview_pages가 있으면 그대로 사용
    layout = spec.get("layout", {}) if isinstance(spec.get("layout", {}), dict) else {}
    pp = layout.get("preview_pages")
    if isinstance(pp, (list, tuple)) and len(pp) == 3:
        return int(pp[0]), int(pp[1]), int(pp[2])

    # 없으면: cover + 중간 2장
    page_count = int(layout.get("page_count", 3) or 3)
    if page_count <= 3:
        return (0, 1, 2) if page_count == 3 else (0, 0, 0)
    return (0, min(2, page_count - 1), min(3, page_count - 1))


def _render_page_to_png(doc: fitz.Document, page_index: int, out_path: Path, min_px: int = 2200) -> None:
    page = doc.load_page(page_index)

    # 페이지를 렌더링한 결과가 min_px(짧은 변 기준) 이상이 되도록 스케일을 잡는다.
    # A4/Letter 기준 기본 렌더는 너무 작게 나오는 경우가 있어 확대 필요.
    rect = page.rect
    short_side = min(rect.width, rect.height)

    # 72dpi 기준을 가정하고, 대략 min_px 확보하도록 zoom 결정
    # (정확 dpi 계산이 아니어도, 결과 픽셀 기준으로 충분히 큰 이미지를 얻는 게 목적)
    zoom = max(2.0, min_px / float(short_side))
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=mat, alpha=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_path))


def render_previews(spec: dict, pdf_path: Path) -> Tuple[Path, Path, Path]:
    p1 = artifact_path(spec["slug"], "preview_1")
    p2 = artifact_path(spec["slug"], "preview_2")
    p3 = artifact_path(spec["slug"], "preview_3")

    i1, i2, i3 = _pick_preview_pages(spec)

    with fitz.open(pdf_path) as doc:
        _render_page_to_png(doc, i1, p1)
        _render_page_to_png(doc, i2, p2)
        _render_page_to_png(doc, i3, p3)

    return p1, p2, p3

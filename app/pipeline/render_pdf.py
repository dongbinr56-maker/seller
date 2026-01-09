from __future__ import annotations

from pathlib import Path
from typing import Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from ..config import DISCLAIMER_TEXT, load_style_preset
from ..storage import artifact_path


def _hex_to_color(value: str) -> colors.Color:
    value = value.lstrip("#")
    return colors.HexColor(f"#{value}")


def _draw_header_footer(canv: canvas.Canvas, title: str, style: dict, page_width: float, page_height: float) -> None:
    canv.setFont(style["font_name"], style["header_size"])
    canv.setFillColor(_hex_to_color(style["primary_color"]))
    canv.drawString(style["margin"], page_height - style["margin"], title)

    canv.setFont(style["font_name"], style["footer_size"])
    canv.setFillColor(_hex_to_color(style["secondary_color"]))
    canv.drawString(style["margin"], style["margin"] / 2, DISCLAIMER_TEXT)


def _draw_grid(canv: canvas.Canvas, style: dict, page_width: float, page_height: float, rows: int, cols: int) -> None:
    start_x = style["margin"]
    start_y = page_height - style["margin"] * 2
    cell_width = style["col_width"]
    cell_height = style["row_height"]
    canv.setStrokeColor(_hex_to_color(style["grid_color"]))
    for row in range(rows + 1):
        y = start_y - row * cell_height
        canv.line(start_x, y, start_x + cols * cell_width, y)
    for col in range(cols + 1):
        x = start_x + col * cell_width
        canv.line(x, start_y, x, start_y - rows * cell_height)


def _draw_checkbox_row(canv: canvas.Canvas, style: dict, page_width: float, page_height: float) -> None:
    start_x = style["margin"]
    start_y = page_height - style["margin"] * 3
    size = 12
    for i in range(6):
        x = start_x + i * (size + 20)
        canv.rect(x, start_y, size, size)
        canv.drawString(x + size + 4, start_y + 2, f"Item {i + 1}")


def render_pdf(spec: dict, page_size: Tuple[float, float], output_path: Path) -> None:
    style = load_style_preset()
    canv = canvas.Canvas(str(output_path), pagesize=page_size)
    page_width, page_height = page_size

    # Page 1: cover + how to use
    _draw_header_footer(canv, spec["title"], style, page_width, page_height)
    canv.setFont(style["font_name"], style["title_size"])
    canv.setFillColor(_hex_to_color(style["primary_color"]))
    canv.drawString(style["margin"], page_height - style["margin"] * 1.5, spec["title"])

    canv.setFont(style["font_name"], style["body_size"])
    canv.setFillColor(_hex_to_color(style["secondary_color"]))
    how_to = [
        "How to use:",
        "1. Print as many pages as you need.",
        "2. Fill in daily or weekly sections.",
        "3. Review progress and adjust.",
    ]
    for index, line in enumerate(how_to):
        canv.drawString(style["margin"], page_height - style["margin"] * (3 + index * 0.6), line)
    canv.showPage()

    # Page 2: tracker layout
    _draw_header_footer(canv, spec["title"], style, page_width, page_height)
    canv.setFont(style["font_name"], style["header_size"])
    canv.setFillColor(_hex_to_color(style["primary_color"]))
    canv.drawString(style["margin"], page_height - style["margin"] * 1.5, "Main Tracker")
    _draw_grid(canv, style, page_width, page_height, rows=8, cols=5)
    _draw_checkbox_row(canv, style, page_width, page_height)
    canv.showPage()

    # Page 3: notes/summary layout
    _draw_header_footer(canv, spec["title"], style, page_width, page_height)
    canv.setFont(style["font_name"], style["header_size"])
    canv.setFillColor(_hex_to_color(style["primary_color"]))
    canv.drawString(style["margin"], page_height - style["margin"] * 1.5, "Notes & Summary")
    _draw_grid(canv, style, page_width, page_height, rows=10, cols=4)
    canv.setFont(style["font_name"], style["body_size"])
    canv.setFillColor(_hex_to_color(style["secondary_color"]))
    canv.drawString(style["margin"], page_height - style["margin"] * 2.5, "Highlights")
    canv.drawString(style["margin"], page_height - style["margin"] * 3.0, "Next Steps")
    canv.showPage()

    canv.save()


def render_pdfs(spec: dict) -> tuple[Path, Path]:
    a4_path = artifact_path(spec["slug"], "pdf_a4")
    us_path = artifact_path(spec["slug"], "pdf_usletter")
    render_pdf(spec, A4, a4_path)
    render_pdf(spec, LETTER, us_path)
    return a4_path, us_path

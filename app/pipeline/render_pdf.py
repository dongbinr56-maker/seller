from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.pdfgen import canvas

from ..config import DISCLAIMER_TEXT, load_style_preset
from ..storage import artifact_path


def _hex(value: str, default=colors.black) -> colors.Color:
    if not value:
        return default
    try:
        return colors.HexColor("#" + str(value).lstrip("#"))
    except Exception:
        return default


def _s(style: dict, key: str, default):
    return style.get(key, default)


THEME_OVERRIDES: Dict[str, Dict[str, str]] = {
    "blue_minimal": {
        "primary_color": "#1F4E79",
        "secondary_color": "#6B7280",
        "grid_color": "#D1D5DB",
        "header_fill": "#F3F6FA",
        # UI variance
        "header_style": "line",          # line | bar
        "section_style": "underline",    # underline | pill | bar_left
        "card_radius": "12",
        "table_radius": "12",
    },
    "charcoal_mono": {
        "primary_color": "#111827",
        "secondary_color": "#6B7280",
        "grid_color": "#D1D5DB",
        "header_fill": "#F4F4F5",
        "header_style": "bar",
        "section_style": "bar_left",
        "card_radius": "6",
        "table_radius": "10",
    },
    "warm_neutral": {
        "primary_color": "#7C4A2D",
        "secondary_color": "#6B7280",
        "grid_color": "#D9D3CC",
        "header_fill": "#F7F2EE",
        "header_style": "bar",
        "section_style": "pill",
        "card_radius": "16",
        "table_radius": "14",
    },
}



def _fit_font(canv: canvas.Canvas, text: str, font_name: str, base_size: float, max_width: float) -> float:
    """
    폭을 넘어가는 텍스트는 폰트를 줄여서 맞춘다.
    ReportLab canvas는 stringWidth로 텍스트 폭을 측정할 수 있다.
    """
    size = float(base_size)
    while size > 7.0:
        if canv.stringWidth(text, font_name, size) <= max_width:
            return size
        size -= 0.5
    return 7.0


def _wrap_words(canv: canvas.Canvas, text: str, font_name: str, font_size: float, max_width: float) -> List[str]:
    """
    단어 단위 줄바꿈. (긴 bullet/문장을 카드 폭 안에 넣기 위해)
    """
    words = (text or "").split()
    if not words:
        return [""]

    lines: List[str] = []
    cur: List[str] = []

    for w in words:
        test = (" ".join(cur + [w])).strip()
        if canv.stringWidth(test, font_name, font_size) <= max_width:
            cur.append(w)
            continue

        if cur:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            # 단어 하나가 너무 긴 경우: 강제로 넣고 다음 줄
            lines.append(w)

    if cur:
        lines.append(" ".join(cur))

    return lines


def _draw_footer(canv: canvas.Canvas, style: dict, page_w: float, margin: float) -> None:
    font = str(_s(style, "font_name", "Helvetica"))
    size = float(_s(style, "footer_size", 8))
    canv.setFont(font, size)
    canv.setFillColor(_hex(_s(style, "secondary_color", "#6B7280")))
    canv.drawCentredString(page_w / 2, margin * 0.45, DISCLAIMER_TEXT)


def _draw_header(canv: canvas.Canvas, style: dict, title: str, page_w: float, page_h: float, margin: float) -> None:
    font = str(_s(style, "font_name", "Helvetica"))
    primary = _hex(_s(style, "primary_color", "#1F4E79"))
    secondary = _hex(_s(style, "secondary_color", "#6B7280"))
    grid = _hex(_s(style, "grid_color", "#D1D5DB"))
    header_style = str(_s(style, "header_style", "line"))

    if header_style == "bar":
        bar_h = float(_s(style, "header_bar_h", 44))
        canv.setFillColor(primary)
        canv.rect(0, page_h - bar_h, page_w, bar_h, stroke=0, fill=1)

        canv.setFillColor(colors.white)
        canv.setFont(font, float(_s(style, "header_size", 10)))
        canv.drawString(margin, page_h - bar_h + 14, title)

        canv.setFont(font, float(_s(style, "header_size", 9)))
        canv.drawRightString(page_w - margin, page_h - bar_h + 14, f"Page {canv.getPageNumber()}")
        return

    # --- 기존 line 헤더 유지 ---
    y_line = page_h - margin + 10
    canv.setStrokeColor(grid)
    canv.setLineWidth(1)
    canv.line(margin, y_line, page_w - margin, y_line)

    canv.setFont(font, float(_s(style, "header_size", 10)))
    canv.setFillColor(primary)
    canv.drawString(margin, page_h - margin + 18, title)

    canv.setFillColor(secondary)
    canv.setFont(font, float(_s(style, "header_size", 9)))
    canv.drawRightString(page_w - margin, page_h - margin + 18, f"Page {canv.getPageNumber()}")



def _round_card(canv: canvas.Canvas, x: float, y: float, w: float, h: float, style: dict) -> None:
    grid = _hex(_s(style, "grid_color", "#D1D5DB"))
    canv.setStrokeColor(grid)
    canv.setFillColor(colors.white)
    canv.setLineWidth(1)
    canv.roundRect(x, y, w, h, radius=12, stroke=1, fill=1)


def _card_title(canv: canvas.Canvas, x: float, y: float, text: str, style: dict) -> None:
    font = str(_s(style, "font_name", "Helvetica"))
    primary = _hex(_s(style, "primary_color", "#1F4E79"))
    canv.setFillColor(primary)
    canv.setFont(font, float(_s(style, "body_size", 10)) + 1)
    canv.drawString(x, y, text)


def _card_bullets(
    canv: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    lines: List[str],
    style: dict,
    max_lines: int = 8,
) -> None:
    font = str(_s(style, "font_name", "Helvetica"))
    secondary = _hex(_s(style, "secondary_color", "#6B7280"))
    size = float(_s(style, "body_size", 10))

    canv.setFillColor(secondary)
    canv.setFont(font, size)

    yy = y
    usable_w = max(10.0, w)

    out: List[str] = []
    for raw in (lines or []):
        raw = str(raw).strip()
        if not raw:
            continue
        wrapped = _wrap_words(canv, f"- {raw}", font, size, usable_w)
        out.extend(wrapped)

    out = out[:max_lines]

    for line in out:
        canv.drawString(x, yy, line)
        yy -= 14


def _draw_section_title(canv: canvas.Canvas, x: float, y: float, text: str, style: dict) -> None:
    font = str(_s(style, "font_name", "Helvetica"))
    primary = _hex(_s(style, "primary_color", "#1F4E79"))
    grid = _hex(_s(style, "grid_color", "#D1D5DB"))
    section_style = str(_s(style, "section_style", "underline"))

    canv.setFont(font, float(_s(style, "header_size", 12)) + 2)

    if section_style == "pill":
        pad_x = 10
        pad_y = 6
        w = max(90, canv.stringWidth(text, font, float(_s(style, "header_size", 12)) + 2) + 2 * pad_x)
        canv.setFillColor(_hex(_s(style, "header_fill", "#F3F6FA")))
        canv.roundRect(x, y - 18, w, 24, radius=12, stroke=0, fill=1)
        canv.setFillColor(primary)
        canv.drawString(x + pad_x, y - 12, text)
        return

    if section_style == "bar_left":
        canv.setFillColor(primary)
        canv.rect(x, y - 18, 6, 22, stroke=0, fill=1)
        canv.drawString(x + 12, y - 12, text)
        return

    # underline (기존)
    canv.setFillColor(primary)
    canv.drawString(x, y, text)
    canv.setStrokeColor(grid)
    canv.setLineWidth(1)
    canv.line(x, y - 10, x + 280, y - 10)



def _draw_table(
    canv: canvas.Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    headers: List[str],
    weights: List[float],
    rows: int,
    style: dict,
) -> None:
    font = str(_s(style, "font_name", "Helvetica"))
    primary = _hex(_s(style, "primary_color", "#1F4E79"))
    grid = _hex(_s(style, "grid_color", "#D1D5DB"))
    header_fill = _hex(_s(style, "header_fill", "#F3F6FA"))

    cols = len(headers)
    total = max(1e-6, sum(weights))
    col_w = [w * (vw / total) for vw in weights]

    header_h = max(24.0, h * 0.09)
    body_h = h - header_h
    row_h = body_h / max(1, rows)

    # outer
    canv.setStrokeColor(grid)
    canv.setLineWidth(1.2)
    canv.roundRect(x, y_top - h, w, h, radius=12, stroke=1, fill=0)

    # header bg
    canv.setFillColor(header_fill)
    canv.roundRect(x, y_top - header_h, w, header_h, radius=12, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.rect(x, y_top - header_h, w, 12, stroke=0, fill=1)  # 아래쪽 둥근 모서리 느낌 정리

    # grid
    canv.setStrokeColor(colors.Color(0.88, 0.90, 0.92))
    canv.setLineWidth(1)

    cx = x
    for i in range(cols + 1):
        canv.line(cx, y_top, cx, y_top - h)
        if i < cols:
            cx += col_w[i]

    canv.line(x, y_top - header_h, x + w, y_top - header_h)
    for r in range(1, rows + 1):
        yy = y_top - header_h - r * row_h
        canv.line(x, yy, x + w, yy)

    # header text
    base = float(_s(style, "body_size", 10))
    canv.setFillColor(primary)

    cx = x
    for i, label in enumerate(headers):
        cell = col_w[i]
        size = _fit_font(canv, label, font, base, cell - 12)
        canv.setFont(font, size)

        # 세로 중앙에 더 가깝게
        ty = (y_top - header_h) + (header_h - size) / 2 - 1
        canv.drawCentredString(cx + cell / 2, ty, label)
        cx += cell


def _draw_lined_box(
    canv: canvas.Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    title: str,
    style: dict,
    line_gap: float = 18.0,
) -> None:
    font = str(_s(style, "font_name", "Helvetica"))
    primary = _hex(_s(style, "primary_color", "#1F4E79"))
    grid = _hex(_s(style, "grid_color", "#D1D5DB"))

    canv.setStrokeColor(grid)
    canv.setLineWidth(1)
    canv.roundRect(x, y_top - h, w, h, radius=12, stroke=1, fill=0)

    canv.setFillColor(primary)
    canv.setFont(font, float(_s(style, "body_size", 10)) + 1)
    canv.drawString(x + 12, y_top - 18, title)

    canv.setStrokeColor(colors.Color(0.88, 0.90, 0.92))
    yy = y_top - 34
    while yy > (y_top - h + 18):
        canv.line(x + 12, yy, x + w - 12, yy)
        yy -= float(line_gap)

PAGE_LABELS: Dict[str, str] = {
    "included_pages": "Included Pages",
    "print_tips": "Print Tips",
    "back_cover": "Back Cover",
    "quick_start": "Quick Start",
    "notes_summary": "Notes & Summary",
}


def _label_for_page(page_id: str) -> str:
    pid = str(page_id or "").strip()
    if pid in PAGE_LABELS:
        return PAGE_LABELS[pid]
    # snake_case -> Title Case
    return pid.replace("_", " ").strip().title() if pid else "Page"


def _draw_checklist_table(
    canv: canvas.Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    labels: List[str],
    style: dict,
) -> None:
    # 3 columns: Page | Use | Notes
    font = str(_s(style, "font_name", "Helvetica"))
    grid = _hex(_s(style, "grid_color", "#D1D5DB"))
    primary = _hex(_s(style, "primary_color", "#1F4E79"))
    header_fill = _hex(_s(style, "header_fill", "#F3F6FA"))

    radius = float(_s(style, "table_radius", 12))
    canv.roundRect(x, y_top - h, w, h, radius=radius, stroke=1, fill=0)

    canv.setFillColor(header_fill)
    canv.roundRect(x, y_top - header_h, w, header_h, radius=radius, stroke=0, fill=1)

    cols = ["Page", "Use", "Notes"]
    weights = [2.4, 0.6, 2.0]
    total = sum(weights)
    col_w = [w * (vw / total) for vw in weights]

    rows = max(8, min(14, len(labels) + 1))
    header_h = 26
    row_h = (h - header_h) / rows

    canv.setStrokeColor(grid)
    canv.setLineWidth(1.2)
    canv.roundRect(x, y_top - h, w, h, radius=radius, stroke=1, fill=0)

    canv.setFillColor(header_fill)
    canv.roundRect(x, y_top - header_h, w, header_h, radius=radius, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.rect(x, y_top - header_h, w, 10, stroke=0, fill=1)

    # grid lines
    canv.setStrokeColor(colors.Color(0.88, 0.90, 0.92))
    canv.setLineWidth(1)

    cx = x
    for i in range(4):
        canv.line(cx, y_top, cx, y_top - h)
        if i < 3:
            cx += col_w[i]

    canv.line(x, y_top - header_h, x + w, y_top - header_h)
    for r in range(1, rows + 1):
        yy = y_top - header_h - r * row_h
        canv.line(x, yy, x + w, yy)

    # header text
    canv.setFillColor(primary)
    canv.setFont(font, float(_s(style, "body_size", 10)))
    cx = x
    for i, c in enumerate(cols):
        canv.drawCentredString(cx + col_w[i] / 2, y_top - header_h + 8, c)
        cx += col_w[i]

    # row content (Page labels)
    canv.setFillColor(_hex(_s(style, "secondary_color", "#6B7280")))
    canv.setFont(font, float(_s(style, "body_size", 10)))
    start_y = y_top - header_h - row_h + 7

    for i, label in enumerate(labels[:rows]):
        yy = start_y - i * row_h
        canv.drawString(x + 10, yy, label)


def _page_included_pages(canv: canvas.Canvas, spec: dict, style: dict, pw: float, ph: float) -> None:
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Included Pages")

    recipe = spec.get("recipe") if isinstance(spec.get("recipe"), list) else []
    # cover/included/back_cover는 목록에서 빼고 “실사용 페이지”만 보여줌
    skip = {"cover", "included_pages", "back_cover"}
    labels = [_label_for_page(pid) for pid in recipe if str(pid) not in skip]

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin

    _draw_checklist_table(canv, margin, top, w, h, labels, style)
    _draw_footer(canv, style, pw, margin)


def _page_print_tips(canv: canvas.Canvas, spec: dict, style: dict, pw: float, ph: float) -> None:
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Print Tips")

    copy = spec.get("copy", {}) if isinstance(spec.get("copy", {}), dict) else {}
    tips = copy.get("print_tips", []) if isinstance(copy.get("print_tips", []), list) else []

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin

    gap = 18
    left = w * 0.58
    right = w - left - gap

    _draw_lined_box(canv, margin, top, left, h, "Tips", style)
    _draw_lined_box(canv, margin + left + gap, top, right, h, "Your Notes", style)

    # tips text
    font = str(_s(style, "font_name", "Helvetica"))
    secondary = _hex(_s(style, "secondary_color", "#6B7280"))
    canv.setFillColor(secondary)
    canv.setFont(font, float(_s(style, "body_size", 10)))

    yy = top - 46
    for line in tips[:10]:
        for wline in _wrap_words(canv, f"- {str(line)}", font, float(_s(style, "body_size", 10)), left - 26):
            canv.drawString(margin + 12, yy, wline)
            yy -= 14

    _draw_footer(canv, style, pw, margin)


def _page_back_cover(canv: canvas.Canvas, spec: dict, style: dict, pw: float, ph: float) -> None:
    margin = float(_s(style, "margin", 54))
    font = str(_s(style, "font_name", "Helvetica"))
    primary = _hex(_s(style, "primary_color", "#1F4E79"))
    secondary = _hex(_s(style, "secondary_color", "#6B7280"))

    title = str(spec.get("title", "Printable Template")).strip()

    # 상단 얇은 밴드(테마에 따라)
    header_style = str(_s(style, "header_style", "line"))
    if header_style == "bar":
        bar_h = 44
        canv.setFillColor(primary)
        canv.rect(0, ph - bar_h, pw, bar_h, stroke=0, fill=1)

    canv.setFillColor(primary)
    canv.setFont(font, 18)
    canv.drawCentredString(pw / 2, ph - margin - 40, "Thank you")

    canv.setFillColor(secondary)
    canv.setFont(font, 11)
    canv.drawCentredString(pw / 2, ph - margin - 62, f"{title} • Printable + Reusable")

    # 큰 노트 박스
    top = ph - margin - 110
    h = ph - 2 * margin - 200
    w = pw - 2 * margin
    _draw_lined_box(canv, margin, top, w, h, "Notes for next time", style)

    _draw_footer(canv, style, pw, margin)


# -------------------- Pages --------------------
def _page_cover(canv: canvas.Canvas, spec: dict, style: dict, pw: float, ph: float) -> None:
    margin = float(_s(style, "margin", 54))
    font = str(_s(style, "font_name", "Helvetica"))
    primary = _hex(_s(style, "primary_color", "#1F4E79"))
    secondary = _hex(_s(style, "secondary_color", "#6B7280"))

    title = str(spec.get("title", "Printable Template")).strip()
    page_count = int(spec.get("layout", {}).get("page_count", 0) or 0)

    copy = spec.get("copy", {}) if isinstance(spec.get("copy", {}), dict) else {}
    subtitle = str(copy.get("cover_subtitle", "Printable pages you can reuse")).strip()
    included = copy.get("included_lines", []) if isinstance(copy.get("included_lines", []), list) else []
    howto = copy.get("howto_lines", []) if isinstance(copy.get("howto_lines", []), list) else []

    # Top band
    band_h = 70
    canv.setFillColor(primary)
    canv.rect(0, ph - band_h, pw, band_h, stroke=0, fill=1)

    # Title (fit)
    max_w = pw - 2 * margin
    title_size = _fit_font(canv, title, font, float(_s(style, "title_size", 24)), max_w)
    canv.setFillColor(colors.white)
    canv.setFont(font, title_size)
    canv.drawCentredString(pw / 2, ph - 48, title)

    # Subtitle
    canv.setFillColor(secondary)
    canv.setFont(font, float(_s(style, "body_size", 11)))
    canv.drawCentredString(pw / 2, ph - band_h - 18, f"{subtitle} • {page_count} pages • A4 + US Letter")

    # Cards layout (responsive-ish)
    gap = 18
    card_w = (pw - 2 * margin - gap) / 2
    card_h = 170

    top_y = ph - band_h - 60
    card_y = top_y - card_h

    lx = margin
    rx = margin + card_w + gap

    _round_card(canv, lx, card_y, card_w, card_h, style)
    _card_title(canv, lx + 14, card_y + card_h - 26, "Included", style)
    _card_bullets(canv, lx + 14, card_y + card_h - 50, card_w - 28, included, style, max_lines=8)

    _round_card(canv, rx, card_y, card_w, card_h, style)
    _card_title(canv, rx + 14, card_y + card_h - 26, "Quick Start", style)
    _card_bullets(canv, rx + 14, card_y + card_h - 50, card_w - 28, howto, style, max_lines=8)

    # Bottom “How to use” card
    how_h = 150
    how_top = margin + how_h + 24
    _round_card(canv, margin, how_top - how_h, pw - 2 * margin, how_h, style)
    _card_title(canv, margin + 14, how_top - 24, "How to use", style)

    canv.setFillColor(secondary)
    canv.setFont(font, float(_s(style, "body_size", 10)))
    yy = how_top - 48
    for line in howto[:6]:
        for wline in _wrap_words(canv, f"- {str(line)}", font, float(_s(style, "body_size", 10)), pw - 2 * margin - 28):
            canv.drawString(margin + 14, yy, wline)
            yy -= 14

    _draw_footer(canv, style, pw, margin)


def _page_quick_start(canv: canvas.Canvas, spec: dict, style: dict, pw: float, ph: float) -> None:
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Quick Start")

    top = ph - margin - 60
    h = ph - 2 * margin - 120
    gap = 18
    left_w = (pw - 2 * margin - gap) * 0.58
    right_w = (pw - 2 * margin - gap) - left_w

    _draw_lined_box(canv, margin, top, left_w, h, "Checklist", style)
    _draw_lined_box(canv, margin + left_w + gap, top, right_w, h, "Notes", style)

    _draw_footer(canv, style, pw, margin)


# ---------- Page Templates (BUDGET) ----------
def _page_cashflow_monthly(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Monthly Cash Flow")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Month", "Income", "Fixed", "Variable", "Net", "Notes"],
        weights=[1.4, 1.2, 1.2, 1.2, 1.0, 2.0],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_cashflow_weekly(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Weekly Forecast")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Week", "Planned In", "Planned Out", "Actual In", "Actual Out", "Net"],
        weights=[1.2, 1.2, 1.2, 1.2, 1.2, 1.0],
        rows=10,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_bills_due_table(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Bills Due")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Due Date", "Bill", "Amount", "Paid", "Method", "Notes"],
        weights=[1.3, 2.2, 1.2, 0.8, 1.3, 2.2],
        rows=16,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_expense_log(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Expense Log")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Date", "Category", "Description", "Amount", "Payment", "Notes"],
        weights=[1.2, 1.7, 2.6, 1.0, 1.3, 2.0],
        rows=18,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_sinking_funds(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Sinking Funds")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Fund", "Target", "Current", "Monthly Add", "Due", "Notes"],
        weights=[2.0, 1.1, 1.1, 1.1, 1.1, 2.6],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_payment_log(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Payment Log")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Date", "Account", "Amount", "Method", "Balance", "Notes"],
        weights=[1.2, 2.2, 1.1, 1.4, 1.1, 2.0],
        rows=16,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_bills_calendar(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Bills Calendar")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Week", "Bills to Pay", "Amount", "Paid?", "Notes"],
        weights=[1.0, 3.0, 1.2, 1.0, 2.2],
        rows=10,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_category_budget(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Category Budget")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Category", "Budget", "Spent", "Remaining", "Notes"],
        weights=[2.2, 1.2, 1.2, 1.2, 2.4],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_debt_list(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Debt List")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Debt", "Balance", "APR", "Min Pay", "Due", "Notes"],
        weights=[2.2, 1.2, 1.0, 1.1, 1.0, 2.5],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_avalanche(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Avalanche Tracker")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Order", "Debt", "APR", "Payment", "New Balance", "Notes"],
        weights=[0.9, 2.0, 1.0, 1.1, 1.2, 2.8],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_snowball(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Snowball Tracker")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Order", "Debt", "Balance", "Payment", "Paid Off?", "Notes"],
        weights=[0.9, 2.2, 1.2, 1.2, 1.0, 2.5],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_progress_meter(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Progress Meter")

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin

    gap = 18
    left_w = w * 0.55
    right_w = w - left_w - gap

    _draw_lined_box(canv, margin, top, left_w, h, "Milestones", style)
    _draw_lined_box(canv, margin + left_w + gap, top, right_w, h * 0.48, "This Month", style)
    _draw_lined_box(
        canv,
        margin + left_w + gap,
        top - h * 0.48 - gap,
        right_w,
        h * 0.52 - gap,
        "Motivation Notes",
        style,
    )

    _draw_footer(canv, style, pw, margin)


def _page_annual_overview(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Annual Overview")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Month", "Income", "Expenses", "Net", "Top Category", "Notes"],
        weights=[1.2, 1.2, 1.2, 1.0, 1.6, 2.2],
        rows=12,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_monthly_overview(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Monthly Overview")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Week", "Main Focus", "Budget Note", "Appointments", "Must Pay", "Review"],
        weights=[1.0, 2.2, 1.6, 1.6, 1.4, 1.8],
        rows=6,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_income_summary(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Income Summary")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Source", "Planned", "Actual", "Difference", "Frequency", "Notes"],
        weights=[2.2, 1.1, 1.1, 1.1, 1.4, 2.5],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_expense_summary(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Expense Summary")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Category", "Planned", "Actual", "Difference", "Action", "Notes"],
        weights=[2.0, 1.1, 1.1, 1.1, 1.6, 2.4],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_savings_goal_tracker(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Savings Goal Tracker")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Goal", "Target", "Start", "Current", "Next Deposit", "Notes"],
        weights=[2.2, 1.2, 1.0, 1.2, 1.4, 2.6],
        rows=12,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_no_spend_calendar(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "No-Spend Calendar")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        weights=[1, 1, 1, 1, 1, 1, 1],
        rows=6,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_challenge_tracker(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Challenge Tracker")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Day", "Challenge", "Done?", "Reward", "Notes"],
        weights=[0.9, 2.8, 0.9, 1.2, 2.2],
        rows=20,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


# ---------- Page Templates (ADHD / productivity pages) ----------
def _page_inbox_capture(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Inbox Capture")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Captured Thought / Task", "Context", "Quick Tag", "Next?"],
        weights=[3.8, 1.6, 1.2, 1.0],
        rows=18,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_clarify_next_action(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Clarify → Next Action")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Item", "Next Action", "Priority", "When", "Done?"],
        weights=[1.8, 3.2, 1.1, 1.2, 0.9],
        rows=16,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_priority_matrix(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Priority Matrix")

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin

    gap = 16
    box_w = (w - gap) / 2
    box_h = (h - gap) / 2

    _draw_lined_box(canv, margin, top, box_w, box_h, "Urgent + Important", style)
    _draw_lined_box(canv, margin + box_w + gap, top, box_w, box_h, "Not Urgent + Important", style)
    _draw_lined_box(canv, margin, top - box_h - gap, box_w, box_h, "Urgent + Not Important", style)
    _draw_lined_box(canv, margin + box_w + gap, top - box_h - gap, box_w, box_h, "Not Urgent + Not Important", style)

    _draw_footer(canv, style, pw, margin)


def _page_time_block(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Time Block Plan")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Block", "Goal", "Start", "End", "Notes"],
        weights=[1.0, 2.8, 1.0, 1.0, 2.2],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_habit_grid(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Habit Grid (30 Days)")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Habit", "1-5", "6-10", "11-15", "16-20", "21-25", "26-30"],
        weights=[2.2, 1, 1, 1, 1, 1, 1],
        rows=10,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_focus_blocks(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Focus Blocks")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Block", "What I’ll Do", "Start", "End", "Energy", "Notes"],
        weights=[0.9, 2.8, 1.0, 1.0, 1.0, 2.3],
        rows=12,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_deep_work_log(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Deep Work Log")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Date", "Task", "Minutes", "What Helped", "What Blocked"],
        weights=[1.2, 2.6, 1.0, 2.0, 2.2],
        rows=16,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_distraction_log(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Distraction Log")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Time", "Trigger", "What I Did", "Return Plan", "Notes"],
        weights=[1.0, 1.6, 2.4, 1.8, 2.2],
        rows=16,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_break_plan(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Break Plan")

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin

    gap = 16
    left = w * 0.55
    right = w - left - gap

    _draw_lined_box(canv, margin, top, left, h, "Break Ideas", style)
    _draw_lined_box(canv, margin + left + gap, top, right, h * 0.48, "Reset Checklist", style)
    _draw_lined_box(
        canv,
        margin + left + gap,
        top - h * 0.48 - gap,
        right,
        h * 0.52 - gap,
        "After Break",
        style,
    )

    _draw_footer(canv, style, pw, margin)


def _page_mood_checkin(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Mood Check-in")

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin

    _draw_lined_box(canv, margin, top, w, h * 0.55, "How I feel (notes)", style)
    _draw_lined_box(canv, margin, top - h * 0.55 - 18, w, h * 0.45 - 18, "What I’ll do next (small step)", style)

    _draw_footer(canv, style, pw, margin)


def _page_morning_routine(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Morning Routine")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Step", "Cue", "Action", "Time", "Done?", "Notes"],
        weights=[0.9, 1.4, 2.6, 1.0, 0.9, 2.2],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_evening_routine(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Evening Routine")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Step", "Trigger", "Action", "Prep", "Done?", "Notes"],
        weights=[0.9, 1.4, 2.6, 1.0, 0.9, 2.2],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_weekly_routine(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Weekly Routine")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Day", "Anchor Habit", "Priority", "Focus Block", "Notes"],
        weights=[1.0, 2.2, 1.4, 2.0, 2.4],
        rows=7,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_gratitude_log(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Gratitude Log")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Date", "1", "2", "3", "Why it mattered"],
        weights=[1.1, 1.0, 1.0, 1.0, 3.8],
        rows=14,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_weekly_goals(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Weekly Goals")

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin

    gap = 16
    left = w * 0.6
    right = w - left - gap
    _draw_lined_box(canv, margin, top, left, h, "Top 3 Outcomes", style)
    _draw_lined_box(canv, margin + left + gap, top, right, h * 0.48, "Must Do", style)
    _draw_lined_box(canv, margin + left + gap, top - h * 0.48 - gap, right, h * 0.52 - gap, "Nice To Have", style)
    _draw_footer(canv, style, pw, margin)


def _page_daily_priorities(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Daily Priorities")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Day", "One Priority", "Support Tasks", "Time Block", "Done?"],
        weights=[1.0, 2.6, 2.6, 1.6, 0.8],
        rows=7,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_wins_lessons(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Wins & Lessons")

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin

    _draw_lined_box(canv, margin, top, w, h * 0.55, "Wins (what worked)", style)
    _draw_lined_box(canv, margin, top - h * 0.55 - 18, w, h * 0.45 - 18, "Lessons (what to change)", style)
    _draw_footer(canv, style, pw, margin)


def _page_next_week_plan(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Next Week Plan")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Focus", "Carryover", "Start/Stop", "Schedule", "Notes"],
        weights=[1.8, 2.2, 2.2, 1.6, 2.2],
        rows=12,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_project_overview(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Project Overview")

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    gap = 16
    left = w * 0.62
    right = w - left - gap
    _draw_lined_box(canv, margin, top, left, h, "Goal / Definition of Done", style)
    _draw_lined_box(canv, margin + left + gap, top, right, h * 0.48, "Milestone", style)
    _draw_lined_box(canv, margin + left + gap, top - h * 0.48 - gap, right, h * 0.52 - gap, "Risks", style)
    _draw_footer(canv, style, pw, margin)


def _page_task_backlog(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Task Backlog")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Task", "Owner", "Priority", "Estimate", "Status", "Notes"],
        weights=[3.0, 1.2, 1.0, 1.0, 1.2, 2.6],
        rows=16,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_kanban_board(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Kanban Board")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Backlog", "Doing", "Blocked", "Done"],
        weights=[1, 1, 1, 1],
        rows=10,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_milestones(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Milestones")
    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_table(
        canv, margin, top, w, h,
        headers=["Milestone", "Owner", "Target Date", "Status", "Next Step", "Notes"],
        weights=[2.6, 1.2, 1.3, 1.1, 2.0, 2.4],
        rows=12,
        style=style,
    )
    _draw_footer(canv, style, pw, margin)


def _page_meeting_notes(canv, spec, style, pw, ph):
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Meeting Notes")

    top = ph - margin - 60
    h = ph - 2 * margin - 130
    w = pw - 2 * margin
    _draw_lined_box(canv, margin, top, w, h * 0.55, "Notes", style)
    _draw_lined_box(canv, margin, top - h * 0.55 - 18, w, h * 0.45 - 18, "Decisions & Actions", style)
    _draw_footer(canv, style, pw, margin)


def _page_notes_summary(canv: canvas.Canvas, spec: dict, style: dict, pw: float, ph: float) -> None:
    margin = float(_s(style, "margin", 54))
    _draw_header(canv, style, str(spec.get("title", "")), pw, ph, margin)
    _draw_section_title(canv, margin, ph - margin - 18, "Notes & Summary")

    top = ph - margin - 60
    h = ph - 2 * margin - 120
    w = pw - 2 * margin
    gap = 18
    left_w = w * 0.62
    right_w = w - left_w - gap

    _draw_lined_box(canv, margin, top, left_w, h, "Notes", style)
    _draw_lined_box(canv, margin + left_w + gap, top, right_w, h * 0.32, "Highlights", style)
    _draw_lined_box(canv, margin + left_w + gap, top - h * 0.32 - gap, right_w, h * 0.34 - gap, "Next Steps", style)
    _draw_lined_box(canv, margin + left_w + gap, top - h * 0.66 - 2 * gap, right_w, h * 0.34 - gap, "Reminders", style)

    _draw_footer(canv, style, pw, margin)


PAGE_RENDERERS: Dict[str, Callable[[canvas.Canvas, dict, dict, float, float], None]] = {
    "cover": _page_cover,
    "included_pages": _page_included_pages,
    "quick_start": _page_quick_start,
    "print_tips": _page_print_tips,
    "back_cover": _page_back_cover,

    # BUDGET
    "cashflow_monthly": _page_cashflow_monthly,
    "cashflow_weekly": _page_cashflow_weekly,
    "bills_calendar": _page_bills_calendar,
    "bills_due_table": _page_bills_due_table,
    "payment_log": _page_payment_log,
    "category_budget": _page_category_budget,
    "expense_log": _page_expense_log,
    "sinking_funds": _page_sinking_funds,
    "debt_list": _page_debt_list,
    "avalanche_tracker": _page_avalanche,
    "snowball_tracker": _page_snowball,
    "progress_meter": _page_progress_meter,
    "annual_overview": _page_annual_overview,
    "monthly_overview": _page_monthly_overview,
    "income_summary": _page_income_summary,
    "expense_summary": _page_expense_summary,
    "savings_goal_tracker": _page_savings_goal_tracker,
    "no_spend_calendar": _page_no_spend_calendar,
    "challenge_tracker": _page_challenge_tracker,

    # ADHD / productivity
    "inbox_capture": _page_inbox_capture,
    "clarify_next_action": _page_clarify_next_action,
    "priority_matrix": _page_priority_matrix,
    "time_block": _page_time_block,
    "habit_grid": _page_habit_grid,
    "focus_blocks": _page_focus_blocks,
    "deep_work_log": _page_deep_work_log,
    "distraction_log": _page_distraction_log,
    "break_plan": _page_break_plan,
    "mood_checkin": _page_mood_checkin,
    "morning_routine": _page_morning_routine,
    "evening_routine": _page_evening_routine,
    "weekly_routine": _page_weekly_routine,
    "gratitude_log": _page_gratitude_log,
    "weekly_goals": _page_weekly_goals,
    "daily_priorities": _page_daily_priorities,
    "wins_lessons": _page_wins_lessons,
    "next_week_plan": _page_next_week_plan,
    "project_overview": _page_project_overview,
    "task_backlog": _page_task_backlog,
    "kanban_board": _page_kanban_board,
    "milestones": _page_milestones,
    "meeting_notes": _page_meeting_notes,

    "notes_summary": _page_notes_summary,
}


def render_pdf(spec: dict, page_size: Tuple[float, float], output_path: Path) -> None:
    style = load_style_preset()

    theme = str(spec.get("theme", "blue_minimal"))
    style.update(THEME_OVERRIDES.get(theme, {}))

    canv = canvas.Canvas(str(output_path), pagesize=page_size)
    pw, ph = page_size

    recipe = spec.get("recipe") if isinstance(spec.get("recipe"), list) else [
    "cover", "included_pages", "quick_start", "notes_summary", "back_cover"
]
    # page_count는 “사실”인 recipe 길이로 맞춘다
    spec.setdefault("layout", {})
    spec["layout"]["page_count"] = len(recipe)

    for page_id in recipe:
        fn = PAGE_RENDERERS.get(str(page_id))
        if fn is None:
            fn = PAGE_RENDERERS["notes_summary"]
        fn(canv, spec, style, pw, ph)
        canv.showPage()

    canv.save()


def render_pdfs(spec: dict) -> tuple[Path, Path]:
    a4_path = artifact_path(spec["slug"], "pdf_a4")
    us_path = artifact_path(spec["slug"], "pdf_usletter")
    render_pdf(spec, A4, a4_path)
    render_pdf(spec, LETTER, us_path)
    return a4_path, us_path

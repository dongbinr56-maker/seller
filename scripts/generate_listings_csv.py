from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


def _get_pdf_page_count(pdf_path: Path) -> int:
    """
    PDF에서 실제 페이지 수를 읽어온다. (가장 신뢰도 높은 소스)
    - PyMuPDF(fitz)가 설치되어 있으면 정확히 page_count를 반환
    - 없거나 에러면 0 반환(이 경우 metadata의 page_count로 fallback)
    """
    try:
        import fitz  # PyMuPDF
        with fitz.open(pdf_path) as doc:
            return int(doc.page_count)
    except Exception:
        return 0


def _clean_title(niche: str, title: str) -> str:
    """
    판매용 제목을 정리:
    - title 앞에 niche(BUDGET/ADHD)가 붙어 있으면 제거
    - 최소한 Printable / PDF를 포함하도록 정리
    """
    t = (title or "").strip()
    n = (niche or "").strip().upper()

    # title이 "BUDGET xxx"처럼 시작하면 제거
    if n and t.upper().startswith(n + " "):
        t = t[len(n) + 1 :].strip()

    # 너무 짧으면 안전장치
    if not t:
        t = "Printable Planner"

    # 판매용 suffix 보정
    if "Printable" not in t:
        t = f"{t} Printable"
    if "PDF" not in t:
        t = f"{t} PDF"

    return t


def _safe_read_json(path: Path) -> Dict:
    """
    JSON 파일을 안전하게 읽는다.
    - 파일 없으면 즉시 실패
    - 파싱 실패하면 즉시 실패
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e


def _pick_price_usd(page_count: int) -> str:
    """
    페이지 수 기반 기본 가격(USD)
    - 너가 '수익 관련은 알아서'라고 했으니 여기 룰로 고정
    """
    if page_count <= 3:
        return "2.99"
    if page_count <= 6:
        return "3.99"
    if page_count <= 10:
        return "4.99"
    return "5.99"


def _build_tags(niche: str, title: str) -> str:
    """
    태그는 CSV에서 콤마 꼬임 방지를 위해 | 로 구분
    """
    base = ["printable", "planner", "pdf", "a4", "us-letter"]

    niche_u = (niche or "").strip().upper()
    if niche_u == "BUDGET":
        base += ["budget", "money", "finance", "expense-tracker", "savings"]
    elif niche_u == "ADHD":
        # 정책 리스크 줄이기 위해 태그에 ADHD 직접 표기는 피함
        base += ["focus", "routine", "productivity", "daily-planner", "habit-tracker"]
    else:
        base += ["tracker", "organizer"]

    # 제목에서 의미 있는 단어 몇 개만 추가
    title_words = [
        w.lower()
        for w in title.replace("-", " ").split()
        if len(w) >= 4 and w.lower() not in {"planner", "printable", "template", "pdf"}
    ]
    base += title_words[:3]

    # 중복 제거(순서 유지)
    seen = set()
    uniq: List[str] = []
    for t in base:
        if t not in seen:
            seen.add(t)
            uniq.append(t)

    return "|".join(uniq[:20])


def _build_description(title: str, page_count: int, modules: List[str]) -> str:
    """
    마켓 설명 자동 생성
    - 과장/보장 표현 금지
    - 디지털 다운로드 고지 포함
    """
    feature_lines: List[str] = []
    for m in modules:
        if not isinstance(m, str):
            continue
        m = m.strip()
        if not m:
            continue
        feature_lines.append(f"- {m.replace('_', ' ').title()}")

    feature_block = "\n".join(feature_lines) if feature_lines else "- Printable pages"

    return (
        f"{title}\n\n"
        f"Includes {page_count} pages.\n\n"
        f"Formats:\n"
        f"- PDF (A4)\n"
        f"- PDF (US Letter)\n\n"
        f"What's inside:\n"
        f"{feature_block}\n\n"
        f"How it works:\n"
        f"1) Download the ZIP file\n"
        f"2) Open and print the PDF pages you need\n"
        f"3) Fill in by hand and reuse as desired\n\n"
        f"Notes:\n"
        f"- Digital download only (no physical item shipped)\n"
        f"- Colors may vary by printer\n"
    )


def _validate_artifacts(sku_dir: Path, slug: str) -> Tuple[Path, Path, Path, Path, Path, Path, Path, Path]:
    """
    SKU 폴더 내 필수 산출물이 존재하는지 점검하고, 경로를 반환한다.
    """
    bundle_zip = sku_dir / "bundle.zip"
    pdf_a4 = sku_dir / "product_a4.pdf"
    pdf_us = sku_dir / "product_usletter.pdf"
    p1 = sku_dir / "preview_1.png"
    p2 = sku_dir / "preview_2.png"
    p3 = sku_dir / "preview_3.png"
    spec = sku_dir / "spec.json"
    meta = sku_dir / "metadata.json"

    required = [bundle_zip, pdf_a4, pdf_us, p1, p2, p3, spec, meta]
    missing = [p for p in required if not p.exists()]
    if missing:
        missing_list = ", ".join(str(p) for p in missing)
        raise FileNotFoundError(f"[{slug}] Missing required artifacts: {missing_list}")

    return bundle_zip, pdf_a4, pdf_us, p1, p2, p3, spec, meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=str, default="out", help="Root output directory (default: out)")
    parser.add_argument("--csv", type=str, default="out/listings.csv", help="Output CSV path")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    csv_path = Path(args.csv)

    if not out_dir.exists():
        raise FileNotFoundError(f"out-dir not found: {out_dir}")

    # out/* 중 디렉터리만 SKU로 취급 (out/ace.db 같은 파일은 자동 제외)
    sku_dirs = sorted([p for p in out_dir.iterdir() if p.is_dir()])

    rows: List[Dict[str, str]] = []
    for sku_dir in sku_dirs:
        meta_path = sku_dir / "metadata.json"
        if not meta_path.exists():
            # SKU 폴더가 아닌 다른 폴더가 섞였을 가능성 → 스킵
            continue

        meta = _safe_read_json(meta_path)

        # 1) 기본 필드 먼저 확정
        niche = str(meta.get("niche", "")).strip()
        slug = str(meta.get("slug", sku_dir.name)).strip()

        modules = meta.get("modules", [])
        if not isinstance(modules, list):
            modules = []

        layout = meta.get("layout", {})
        if not isinstance(layout, dict):
            layout = {}

        # 2) 산출물 경로 먼저 확보(이후 pdf_a4를 page_count 계산에 사용)
        bundle_zip, pdf_a4, pdf_us, p1, p2, p3, spec, _ = _validate_artifacts(sku_dir, slug)

        # 3) 제목 정리
        title_raw = str(meta.get("title", "")).strip()
        title = _clean_title(niche=niche, title=title_raw)

        # 4) 페이지 수 보정: PDF > metadata
        page_count_meta = int(layout.get("page_count", 0) or 0)
        page_count_pdf = _get_pdf_page_count(pdf_a4)
        page_count = page_count_pdf if page_count_pdf > 0 else page_count_meta

        # 5) 판매용 필드 생성
        tags = _build_tags(niche=niche, title=title)
        description = _build_description(title=title, page_count=page_count, modules=modules)
        price_usd = _pick_price_usd(page_count=page_count)

        rows.append(
            {
                "slug": slug,
                "niche": niche,
                "title_raw": title_raw,
                "title": title,
                "page_count": str(page_count),
                "formats": "PDF(A4)|PDF(US Letter)",
                "bundle_zip": str(bundle_zip),
                "preview_1": str(p1),
                "preview_2": str(p2),
                "preview_3": str(p3),
                "tags": tags,
                "description": description,
                "price_usd": price_usd,
            }
        )

    # CSV 저장(줄바꿈/인코딩 이슈 방지)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "slug",
        "niche",
        "title_raw",
        "title",
        "page_count",
        "formats",
        "bundle_zip",
        "preview_1",
        "preview_2",
        "preview_3",
        "tags",
        "description",
        "price_usd",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"OK: wrote {len(rows)} rows -> {csv_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


def _normalize_newlines(text: str) -> str:
    """
    업로드 시스템/엑셀에서 CSV 줄바꿈 때문에 행이 깨지는 문제를 방지하기 위해
    description 내부 줄바꿈을 안전한 형태로 바꾼다.

    전략:
    - 실제 줄바꿈 문자 \\n / \\r\\n 을 ' \\n ' 같은 "눈에 보이는 문자열"로 치환
    - 또는 공백으로 완전 평탄화 할 수도 있음(원하면 아래 한 줄만 바꾸면 됨)
    """
    if text is None:
        return ""
    t = str(text)

    # 1) Windows/Mac 줄바꿈을 통일해서 처리
    t = t.replace("\r\n", "\n").replace("\r", "\n")

    # 2) 업로드 안정성을 위해 줄바꿈을 ' \\n '으로 치환
    #    (완전 공백 처리 원하면: t = " ".join(t.split()) 로 바꿔도 됨)
    t = t.replace("\n", " \\n ")

    # 3) 너무 연속 공백이 생기면 정리
    t = " ".join(t.split())
    return t


def _tags_pipe_to_commas(tags_pipe: str, max_tags: int = 13) -> str:
    """
    tags 컬럼은 현재 '|' 구분자로 되어있다.
    업로드 시스템에서 흔히 요구하는 'comma-separated' 형태로 변환한다.

    - 최대 개수 제한이 있는 플랫폼들이 많아서 기본 13개로 제한(필요시 변경 가능)
    """
    if not tags_pipe:
        return ""
    tags = [t.strip() for t in tags_pipe.split("|") if t.strip()]

    # 중복 제거(순서 유지)
    seen = set()
    uniq: List[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            uniq.append(t)

    return ", ".join(uniq[:max_tags])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_csv", type=str, default="out/listings.csv", help="Input listings CSV")
    parser.add_argument("--out", dest="out_csv", type=str, default="out/upload_pack.csv", help="Output upload-pack CSV")
    args = parser.parse_args()

    in_path = Path(args.in_csv)
    out_path = Path(args.out_csv)

    if not in_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {in_path}")

    rows: List[Dict[str, str]] = []
    with in_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # 업로드용으로 description을 평탄화하고, tags를 comma로 변환
            r["description"] = _normalize_newlines(r.get("description", ""))
            r["tags"] = _tags_pipe_to_commas(r.get("tags", ""), max_tags=13)
            rows.append(r)

    # 출력 컬럼은 입력 컬럼 그대로 유지 (안전)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"OK: wrote {len(rows)} rows -> {out_path}")


if __name__ == "__main__":
    main()

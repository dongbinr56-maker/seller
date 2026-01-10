from __future__ import annotations

from pathlib import Path
from typing import List
import json


BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "out"
DB_PATH = OUT_DIR / "ace.db"
STYLE_PRESET_PATH = BASE_DIR / "assets" / "brand" / "template_styles.json"

BANNED_WORDS: List[str] = [
    "cure",
    "guarantee",
    "diagnose",
    "treatment",
    "medical",
    "miracle",
]

ALLOWED_NICHES = {"BUDGET", "ADHD"}

DISCLAIMER_TEXT = "This printable is for informational purposes only."
REQUIRED_MODULES = ["cover", "how_to", "tracker", "notes"]


def load_style_preset() -> dict:
    with STYLE_PRESET_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def set_out_dir(path: Path) -> None:
    global OUT_DIR, DB_PATH
    OUT_DIR = path
    DB_PATH = OUT_DIR / "ace.db"

from __future__ import annotations

import tempfile
from pathlib import Path

from app import config
from app.pipeline.render_preview import render_previews


class DummyPixmap:
    def save(self, path: str) -> None:
        Path(path).write_text("preview", encoding="utf-8")


class DummyPage:
    def get_pixmap(self, matrix=None) -> DummyPixmap:  # noqa: ARG002 - signature matches fitz
        return DummyPixmap()


class DummyDoc:
    def __init__(self) -> None:
        self.page_count = 3
        self.closed = False

    def __enter__(self) -> "DummyDoc":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001 - test helper
        self.closed = True

    def load_page(self, index: int) -> DummyPage:  # noqa: ARG002 - test helper
        return DummyPage()


def test_render_previews_closes_document(monkeypatch) -> None:
    doc = DummyDoc()

    def fake_open(path: str) -> DummyDoc:  # noqa: ARG001 - test helper
        return doc

    with tempfile.TemporaryDirectory() as temp_dir:
        config.set_out_dir(Path(temp_dir))
        monkeypatch.setattr("app.pipeline.render_preview.fitz.open", fake_open)
        previews = render_previews("sample", Path("sample.pdf"), base_dir=Path(temp_dir))
        assert doc.closed is True
        assert len(previews) == 3
        assert all(path.exists() for path in previews)

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from app import config
from app.models import reset_engine
from app.pipeline.ingest import slug_from_title
from app.pipeline.metadata import build_metadata
from app.pipeline.qa import validate_spec
from app.pipeline.render_pdf import render_pdfs


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        config.set_out_dir(Path(self.temp_dir.name))
        reset_engine()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_slug_generation(self) -> None:
        self.assertEqual(slug_from_title("Focus Planner"), "focus-planner")

    def test_banned_words(self) -> None:
        spec = {"title": "Miracle Plan", "modules": ["cover", "how_to", "tracker", "notes"], "slug": "test"}
        errors = validate_spec(spec, "Valid description" * 20)
        self.assertTrue(any("Banned" in error for error in errors))

    def test_metadata_length(self) -> None:
        metadata = build_metadata("ADHD", "Focus Planner", "focus-planner")
        self.assertGreaterEqual(len(metadata["description"]), 200)
        self.assertLessEqual(len(metadata["description"]), 400)

    def test_pdf_output(self) -> None:
        spec = {"title": "Focus Planner", "slug": "focus-planner"}
        a4, us = render_pdfs(spec)
        self.assertTrue(a4.exists())
        self.assertTrue(us.exists())


if __name__ == "__main__":
    unittest.main()

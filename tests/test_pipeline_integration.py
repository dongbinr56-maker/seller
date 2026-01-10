from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from app import config
from app.models import reset_engine
from app.pipeline.ingest import ingest_products
from app.pipeline.run import run_pipeline


def test_pipeline_outputs_expected_artifacts() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        out_dir = Path(temp_dir) / "out"
        config.set_out_dir(out_dir)
        reset_engine()
        csv_path = Path(temp_dir) / "products.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["niche", "title"])
            writer.writeheader()
            writer.writerow({"niche": "ADHD", "title": "Focus Planner"})
            writer.writerow({"niche": "BUDGET", "title": "Budget Tracker"})
        products = ingest_products(csv_path)
        results = run_pipeline(products)
        assert len(results["READY"]) == 2
        for slug in results["READY"]:
            product_dir = out_dir / slug
            assert (product_dir / "a4.pdf").exists()
            assert (product_dir / "letter.pdf").exists()
            assert (product_dir / "preview_1.png").exists()
            assert (product_dir / "preview_2.png").exists()
            assert (product_dir / "preview_3.png").exists()
            assert (product_dir / "spec.json").exists()
            assert (product_dir / "metadata.json").exists()
            assert (product_dir / "bundle.zip").exists()
            assert (product_dir / "README.txt").exists()

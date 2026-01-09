from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import config
from .models import ProductStatus, reset_engine
from .pipeline.ingest import ingest_products, list_products
from .pipeline.run import run_pipeline

app = typer.Typer(help="Digital template production pipeline")


@app.command()
def build(
    csv: Optional[Path] = typer.Option(None, "--csv", help="CSV path with niche/title"),
    out: Optional[Path] = typer.Option(None, "--out", help="Output directory"),
    niche: Optional[str] = typer.Option(None, "--niche", help="Filter by niche"),
    dry_run_ingest: bool = typer.Option(False, "--dry-run-ingest", help="Only ingest CSV"),
) -> None:
    if out:
        config.set_out_dir(out)
        reset_engine()
    if csv:
        products = ingest_products(csv)
        typer.echo(f"Ingested {len(products)} products")
        if dry_run_ingest:
            return
    statuses = [ProductStatus.DRAFT]
    products = list_products(statuses, niche=niche)
    if not products:
        typer.echo("No products to process")
        return
    results = run_pipeline(products)
    typer.echo(f"READY: {len(results['READY'])}")
    typer.echo(f"FAILED: {len(results['FAILED'])}")
    for product in results["FAILED"]:
        typer.echo(f"FAILED: {product.sku_slug}")


@app.command()
def retry(
    out: Optional[Path] = typer.Option(None, "--out", help="Output directory"),
    failed: bool = typer.Option(True, "--failed", help="Retry failed only"),
) -> None:
    if out:
        config.set_out_dir(out)
        reset_engine()
    statuses = [ProductStatus.FAILED] if failed else [ProductStatus.DRAFT]
    products = list_products(statuses)
    if not products:
        typer.echo("No products to retry")
        return
    results = run_pipeline(products)
    typer.echo(f"READY: {len(results['READY'])}")
    typer.echo(f"FAILED: {len(results['FAILED'])}")


if __name__ == "__main__":
    app()

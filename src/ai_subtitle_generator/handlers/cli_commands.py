"""Typer command handlers — thin wrappers over the pipeline."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ai_subtitle_generator.core.loader import bootstrap_plugins
from ai_subtitle_generator.core.pipeline import PipelineRequest, run_pipeline
from ai_subtitle_generator.services.config import load_config

console = Console()


def _registries():
    cfg = load_config()
    roots = [Path(p) for p in cfg.get("plugins", {}).get("paths", ["plugins"])]
    return bootstrap_plugins(roots)


def generate(
    media: Path = typer.Argument(..., exists=True, readable=True, help="Input audio/video file."),
    output: Path | None = typer.Option(None, "--out", "-o", help="Output caption path."),
    transcriber: str | None = typer.Option(None, "--transcriber", help="Transcriber plugin name."),
    formatter: str | None = typer.Option(None, "--format", "-f", help="Formatter plugin name."),
    language: str | None = typer.Option(None, "--lang", "-l", help="Source language or 'auto'."),
) -> None:
    """Generate subtitles for a media file."""
    regs = _registries()
    req = PipelineRequest(
        media_path=media,
        output_path=output,
        transcriber=transcriber,
        formatter=formatter,
        target_language=language,
    )

    def _progress(stage: str, frac: float) -> None:
        console.print(f"[dim]{stage:<11}[/dim] {int(frac * 100):>3}%")

    result = run_pipeline(req, regs, progress=_progress)
    console.print(f"[green]wrote[/green] {result.output_path} ({len(result.segments)} segments, "
                  f"{result.elapsed_s:.2f}s via {result.backend})")


def list_plugins() -> None:
    """List every loaded plugin, grouped by kind."""
    regs = _registries()
    table = Table(title="Loaded plugins")
    table.add_column("kind", style="cyan")
    table.add_column("name", style="bold")
    for kind, names in regs.summary().items():
        for n in names:
            table.add_row(kind, n)
    console.print(table)
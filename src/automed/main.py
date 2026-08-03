"""CLI entrypoint for AutoMed consultations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import structlog
import typer
from rich.console import Console
from rich.markdown import Markdown

from automed import __version__
from automed.config import get_settings
from automed.orchestration.group_chat import AutoMedOrchestrator

app = typer.Typer(
    name="automed",
    help="Multi-Agent Healthcare Assistant powered by AG2 (AutoGen).",
    add_completion=False,
)
console = Console()


def _configure_logging(level: str) -> None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), level.upper(), 20)
        ),
    )


@app.command()
def consult(
    query: str = typer.Argument(..., help="Patient symptom / concern description"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path to write the ConsultationReport JSON",
    ),
) -> None:
    """Run a full multi-agent healthcare consultation."""
    settings = get_settings()
    _configure_logging(settings.log_level)

    console.print(
        f"[bold cyan]AutoMed[/bold cyan] v{__version__} — AG2 multi-agent consultation\n"
    )

    orchestrator = AutoMedOrchestrator(settings)
    report = orchestrator.run(query)

    console.print(Markdown(report.format()))

    if output:
        output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"\n[green]Saved structured report →[/green] {output}")


@app.command()
def version() -> None:
    """Print package version."""
    console.print(__version__)


@app.command("print-schema")
def print_schema() -> None:
    """Print JSON Schema for the final ConsultationReport (integration aid)."""
    from automed.models.schemas import ConsultationReport

    console.print_json(json.dumps(ConsultationReport.model_json_schema(), indent=2))


if __name__ == "__main__":
    app()

"""Typer application for CLI."""

from pathlib import Path
from typing import Annotated

import typer

from setup_repo.cli.commands.cleanup import cleanup
from setup_repo.cli.commands.init import init
from setup_repo.cli.commands.sync import sync
from setup_repo.models.config import get_settings
from setup_repo.utils.logging import configure_logging, get_logger

app = typer.Typer(
    name="setup-repo",
    help="GitHub repository setup and sync tool",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Register commands
app.command()(init)
app.command()(sync)
app.command()(cleanup)

log = get_logger(__name__)


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Show only summary"),
    ] = False,
    log_file: Annotated[
        Path | None,
        typer.Option("--log-file", help="JSON log file path"),
    ] = None,
) -> None:
    """Setup Repository CLI."""
    level = "DEBUG" if verbose else "WARNING" if quiet else "INFO"
    settings = get_settings()
    configure_logging(
        level=level,
        log_file=log_file or settings.log_file,
    )

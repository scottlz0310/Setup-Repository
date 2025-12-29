"""CLI commands."""

from setup_repo.cli.commands.cleanup import cleanup
from setup_repo.cli.commands.init import init
from setup_repo.cli.commands.sync import sync

__all__ = ["cleanup", "init", "sync"]

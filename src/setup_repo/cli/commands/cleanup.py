"""Cleanup command for CLI."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from setup_repo.cli.output import show_error, show_success
from setup_repo.core.git import GitOperations
from setup_repo.utils.console import console
from setup_repo.utils.logging import get_logger

log = get_logger(__name__)


def cleanup(
    path: Annotated[
        Path | None,
        typer.Argument(help="Target repository path"),
    ] = None,
    base_branch: Annotated[
        str,
        typer.Option("--base", "-b", help="Base branch name"),
    ] = "main",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview without deleting"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Delete without confirmation"),
    ] = False,
) -> None:
    """Delete merged branches."""
    repo_path = path or Path.cwd()

    if not (repo_path / ".git").exists():
        show_error("Not a Git repository")
        raise typer.Exit(1)

    git = GitOperations()

    # First fetch --prune
    git.fetch_and_prune(repo_path)

    # Get merged branches
    branches = git.get_merged_branches(repo_path, base_branch)

    if not branches:
        show_success("No branches to delete")
        raise typer.Exit(0)

    # Show table
    table = Table(title="Merged Branches")
    table.add_column("Branch", style="cyan")

    for branch in branches:
        table.add_row(branch)

    console.print(table)

    if dry_run:
        console.print(f"\n[dim]{len(branches)} branch(es) would be deleted[/]")
        raise typer.Exit(0)

    # Confirmation
    if not force:
        confirm = typer.confirm(f"Delete {len(branches)} branch(es)?")
        if not confirm:
            raise typer.Abort()

    # Delete branches
    deleted = 0
    for branch in branches:
        if git.delete_branch(repo_path, branch):
            deleted += 1

    show_success(f"{deleted}/{len(branches)} branch(es) deleted")

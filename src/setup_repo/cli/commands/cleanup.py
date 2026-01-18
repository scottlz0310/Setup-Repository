"""Cleanup command for CLI."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from setup_repo.cli.output import show_error, show_success, show_warning
from setup_repo.core.branch_cleanup import get_squash_merged_branches
from setup_repo.core.git import GitOperations
from setup_repo.models.config import get_settings
from setup_repo.utils.console import console


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
    include_squash: Annotated[
        bool,
        typer.Option("--include-squash", "-s", help="Include squash-merged branches (requires GitHub API)"),
    ] = False,
) -> None:
    """Delete merged branches."""
    repo_path = path or Path.cwd()

    if not (repo_path / ".git").exists():
        show_error("Not a Git repository")
        raise typer.Exit(1)

    git = GitOperations()
    settings = get_settings()

    # First fetch --prune
    git.fetch_and_prune(repo_path)

    # Get merged branches (these can be safely deleted with -d)
    merged_branches = git.get_merged_branches(repo_path, base_branch)

    # Track which branches need force delete
    squash_merged_branches: list[str] = []

    # If include_squash is enabled, also check GitHub API for squash-merged branches
    if include_squash:
        merged_set = set(merged_branches)
        squash_branches = get_squash_merged_branches(
            git,
            repo_path,
            base_branch,
            github_token=settings.github_token,
            git_ssl_no_verify=settings.git_ssl_no_verify,
            warn=show_warning,
        )
        for branch in squash_branches:
            if branch not in merged_set:
                squash_merged_branches.append(branch)

    # Combine all branches
    all_branches = merged_branches + squash_merged_branches

    if not all_branches:
        show_success("No branches to delete")
        raise typer.Exit(0)

    # Show table
    table = Table(title="Merged Branches")
    table.add_column("Branch", style="cyan")
    if include_squash and squash_merged_branches:
        table.add_column("Type", style="dim")

    for branch in merged_branches:
        if include_squash and squash_merged_branches:
            table.add_row(branch, "merged")
        else:
            table.add_row(branch)

    for branch in squash_merged_branches:
        table.add_row(branch, "squash")

    console.print(table)

    if dry_run:
        console.print(f"\n[dim]{len(all_branches)} branch(es) would be deleted[/]")
        if squash_merged_branches:
            console.print(f"[dim]({len(squash_merged_branches)} squash-merged, will use force delete)[/]")
        raise typer.Exit(0)

    # Confirmation
    if not force:
        msg = f"Delete {len(all_branches)} branch(es)?"
        if squash_merged_branches:
            msg += f" ({len(squash_merged_branches)} will be force-deleted)"
        confirm = typer.confirm(msg)
        if not confirm:
            raise typer.Abort()

    # Delete branches
    deleted = 0
    for branch in merged_branches:
        if git.delete_branch(repo_path, branch, force=False):
            deleted += 1

    for branch in squash_merged_branches:
        if git.delete_branch(repo_path, branch, force=True):
            deleted += 1

    show_success(f"{deleted}/{len(all_branches)} branch(es) deleted")

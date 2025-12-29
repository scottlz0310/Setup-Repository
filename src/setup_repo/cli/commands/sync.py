"""Sync command for CLI."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from setup_repo.cli.output import show_error, show_info, show_summary, show_warning
from setup_repo.core.git import GitOperations
from setup_repo.core.github import GitHubClient
from setup_repo.core.parallel import ParallelProcessor
from setup_repo.models.config import get_settings
from setup_repo.models.repository import Repository
from setup_repo.models.result import ProcessResult, ResultStatus
from setup_repo.utils.console import console
from setup_repo.utils.logging import get_logger

log = get_logger(__name__)


def sync(
    owner: Annotated[
        str | None,
        typer.Option("--owner", "-o", help="GitHub owner name"),
    ] = None,
    dest: Annotated[
        Path | None,
        typer.Option("--dest", "-d", help="Destination directory for cloning"),
    ] = None,
    jobs: Annotated[
        int,
        typer.Option("--jobs", "-j", help="Number of parallel jobs"),
    ] = 10,
    no_prune: Annotated[
        bool,
        typer.Option("--no-prune", help="Skip fetch --prune"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview without executing"),
    ] = False,
) -> None:
    """Sync repositories from GitHub."""
    settings = get_settings()

    owner = owner or settings.github_owner
    if not owner:
        show_error("GitHub owner is not specified")
        raise typer.Exit(1)

    dest_dir = dest or settings.workspace_dir
    dest_dir.mkdir(parents=True, exist_ok=True)

    log.debug("sync_started", owner=owner, dest=str(dest_dir), jobs=jobs)
    show_info(f"Syncing repositories for [cyan]{owner}[/] to [dim]{dest_dir}[/]")

    # Get repository list
    log.debug("fetching_repositories", owner=owner)
    client = GitHubClient(
        token=settings.github_token,
        verify_ssl=not settings.git_ssl_no_verify,
    )

    try:
        repos = client.get_repositories(owner)
        log.info("repositories_fetched", owner=owner, count=len(repos))
    finally:
        client.close()

    if not repos:
        show_warning("No repositories found")
        raise typer.Exit(0)

    show_info(f"Found [cyan]{len(repos)}[/] repositories")

    # Dry-run mode
    if dry_run:
        _show_dry_run(repos, dest_dir)
        raise typer.Exit(0)

    # Sync processing
    git = GitOperations(
        auto_prune=not no_prune,
        ssl_no_verify=settings.git_ssl_no_verify,
    )
    processor = ParallelProcessor(max_workers=jobs)

    log.debug("sync_config", auto_prune=not no_prune, ssl_no_verify=settings.git_ssl_no_verify)

    def process_repo(repo_path: Path) -> ProcessResult:
        if repo_path.exists():
            log.debug("pulling", repo=repo_path.name)
            return git.pull(repo_path)
        else:
            # Find corresponding repository
            repo = next((r for r in repos if r.name == repo_path.name), None)
            if repo:
                log.debug("cloning", repo=repo_path.name, url=repo.get_clone_url(settings.use_https))
                return git.clone(
                    repo.get_clone_url(settings.use_https),
                    repo_path,
                    repo.default_branch,
                )
            return ProcessResult(
                repo_name=repo_path.name,
                status=ResultStatus.SKIPPED,
                message="Repository not found",
            )

    paths = [dest_dir / repo.name for repo in repos]
    summary = processor.process(paths, process_repo, desc="Syncing")

    log.info(
        "sync_completed",
        total=summary.total,
        success=summary.success,
        failed=summary.failed,
        skipped=summary.skipped,
        duration=f"{summary.duration:.1f}s",
    )

    show_summary(summary)

    if summary.failed > 0:
        raise typer.Exit(1)


def _show_dry_run(repos: list[Repository], dest_dir: Path) -> None:
    """Show dry-run preview."""
    table = Table(title="Repositories to sync")
    table.add_column("Repository", style="cyan")
    table.add_column("Action", style="green")
    table.add_column("Path", style="dim")

    for repo in repos:
        repo_path = dest_dir / repo.name
        action = "Pull" if repo_path.exists() else "Clone"
        table.add_row(repo.name, action, str(repo_path))

    console.print(table)
    console.print(f"\n[dim]{len(repos)} repository(ies) would be synced[/]")

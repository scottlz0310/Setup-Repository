"""Sync command for CLI."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from setup_repo.cli.output import show_error, show_info, show_success, show_summary, show_warning
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

    repo_by_name = {repo.name: repo for repo in repos}
    cleanup_stats = {"total_deleted": 0, "total_repos": 0}

    def process_repo(repo_path: Path) -> ProcessResult:
        repo = repo_by_name.get(repo_path.name)
        if repo_path.exists():
            log.debug("pulling", repo=repo_path.name)
            result = git.pull(repo_path)
        else:
            # Find corresponding repository
            if repo:
                log.debug("cloning", repo=repo_path.name, url=repo.get_clone_url(settings.use_https))
                result = git.clone(
                    repo.get_clone_url(settings.use_https),
                    repo_path,
                    repo.default_branch,
                )
            else:
                result = ProcessResult(
                    repo_name=repo_path.name,
                    status=ResultStatus.SKIPPED,
                    message="Repository not found",
                )

        if settings.auto_cleanup and result.status == ResultStatus.SUCCESS:
            base_branch = repo.default_branch if repo else "main"
            deleted = _run_auto_cleanup(git, repo_path, base_branch)
            if deleted > 0:
                cleanup_stats["total_deleted"] += deleted
                cleanup_stats["total_repos"] += 1

        return result

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

    # Show auto-cleanup results if enabled
    if settings.auto_cleanup and cleanup_stats["total_deleted"] > 0:
        show_success(
            f"Auto-cleanup: {cleanup_stats['total_deleted']} merged branch(es) deleted "
            f"across {cleanup_stats['total_repos']} repository(ies)"
        )

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


def _run_auto_cleanup(git: GitOperations, repo_path: Path, base_branch: str) -> int:
    """Auto cleanup merged branches after sync.

    Args:
        git: GitOperations instance
        repo_path: Repository path
        base_branch: Base branch name for merge check

    Returns:
        Number of branches deleted
    """
    if not (repo_path / ".git").exists():
        log.debug("auto_cleanup_skipped_not_git", repo=repo_path.name)
        return 0

    merged_branches = git.get_merged_branches(repo_path, base_branch)
    if not merged_branches:
        log.debug("auto_cleanup_no_branches", repo=repo_path.name, base=base_branch)
        return 0

    deleted = 0
    for branch in merged_branches:
        if git.delete_branch(repo_path, branch, force=False):
            deleted += 1
        else:
            log.warning("delete_branch_failed", repo=repo_path.name, branch=branch)

    log.info(
        "auto_cleanup_completed",
        repo=repo_path.name,
        base=base_branch,
        deleted=deleted,
        total=len(merged_branches),
    )
    return deleted

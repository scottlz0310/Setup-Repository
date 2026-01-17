"""Cleanup command for CLI."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from setup_repo.cli.output import show_error, show_success, show_warning
from setup_repo.core.git import GitOperations
from setup_repo.core.github import GitHubClient
from setup_repo.models.config import get_settings
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

    # First fetch --prune
    git.fetch_and_prune(repo_path)

    # Get merged branches (these can be safely deleted with -d)
    merged_branches = git.get_merged_branches(repo_path, base_branch)

    # Track which branches need force delete
    squash_merged_branches: list[str] = []
    
    # If include_squash is enabled, also check GitHub API for squash-merged branches
    if include_squash:
        merged_set = set(merged_branches)
        squash_branches = _get_squash_merged_branches(git, repo_path, base_branch)
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


def _get_squash_merged_branches(git: GitOperations, repo_path: Path, base_branch: str) -> list[str]:
    """Get branches that were squash-merged via GitHub.

    Args:
        git: GitOperations instance
        repo_path: Repository path
        base_branch: Base branch name

    Returns:
        List of branch names that were squash-merged
    """
    # Get remote URL and parse owner/repo
    remote_url = git.get_remote_url(repo_path)
    if not remote_url:
        log.warning("no_remote_url", repo=repo_path.name)
        show_warning("Could not detect GitHub repository from remote URL")
        return []

    repo_info = git.parse_github_repo(remote_url)
    if not repo_info:
        log.warning("not_github_repo", remote_url=remote_url)
        show_warning("Remote URL is not a GitHub repository")
        return []

    owner, repo = repo_info

    # Get GitHub token from settings
    settings = get_settings()
    if not settings.github_token:
        log.warning("no_github_token")
        show_warning("GitHub token not found. Set SETUP_REPO_GITHUB_TOKEN or run 'setup-repo init'")
        return []

    # Fetch merged PRs from GitHub API
    try:
        with GitHubClient(token=settings.github_token, verify_ssl=not settings.git_ssl_no_verify) as client:
            merged_prs = client.get_merged_pull_requests(owner, repo, base_branch)
    except Exception as e:
        log.error("failed_to_fetch_merged_prs", error=str(e))
        show_warning(f"Failed to fetch merged PRs from GitHub: {e}")
        return []

    # Get local branches
    local_branches = git.get_local_branches(repo_path)
    
    # Get current branch to exclude it
    current_branch = git.get_current_branch(repo_path)

    # Filter branches
    squash_merged: list[str] = []
    for branch in local_branches:
        # Exclude base branch and current branch
        if branch == base_branch or branch == current_branch:
            continue
        
        # Check if this branch was merged as a PR
        if branch not in merged_prs:
            continue
            
        # Verify that the local branch head matches or is ancestor of the PR head
        # This prevents deleting branches that have been reused or have new commits
        pr_head_sha = merged_prs[branch]
        if not pr_head_sha:
            log.warning("no_pr_head_sha", branch=branch)
            continue
            
        local_branch_sha = git.get_branch_sha(repo_path, branch)
        if not local_branch_sha:
            log.warning("no_local_branch_sha", branch=branch)
            continue
        
        # Check if local branch head is the same as PR head or PR head is ancestor
        # (PR head is ancestor means local branch has new commits after merge)
        if local_branch_sha == pr_head_sha:
            # Exact match - safe to delete
            squash_merged.append(branch)
        elif git.is_ancestor(repo_path, pr_head_sha, local_branch_sha):
            # PR head is ancestor of local branch - local has new commits, skip
            log.info("branch_has_new_commits", branch=branch, pr_sha=pr_head_sha, local_sha=local_branch_sha)
        else:
            # Branches have diverged or local is older - skip for safety
            log.info("branch_diverged", branch=branch, pr_sha=pr_head_sha, local_sha=local_branch_sha)

    log.info("found_squash_merged_branches", count=len(squash_merged))
    return squash_merged

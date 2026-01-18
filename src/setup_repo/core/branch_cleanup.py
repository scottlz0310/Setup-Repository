"""Helpers for branch cleanup."""

from collections.abc import Callable
from pathlib import Path

from setup_repo.core.git import GitOperations
from setup_repo.core.github import GitHubClient
from setup_repo.utils.logging import get_logger

log = get_logger(__name__)


def get_squash_merged_branches(
    git: GitOperations,
    repo_path: Path,
    base_branch: str,
    *,
    github_token: str | None,
    git_ssl_no_verify: bool,
    warn: Callable[[str], None] | None = None,
) -> list[str]:
    """Get branches that were squash-merged via GitHub."""
    remote_url = git.get_remote_url(repo_path)
    if not remote_url:
        log.warning("no_remote_url", repo=repo_path.name)
        if warn:
            warn("Could not detect GitHub repository from remote URL")
        return []

    repo_info = git.parse_github_repo(remote_url)
    if not repo_info:
        log.warning("not_github_repo", remote_url=remote_url)
        if warn:
            warn("Remote URL is not a GitHub repository")
        return []

    owner, repo = repo_info

    if not github_token:
        log.warning("no_github_token")
        if warn:
            warn("GitHub token not found. Set SETUP_REPO_GITHUB_TOKEN or run 'setup-repo init'")
        return []

    try:
        with GitHubClient(token=github_token, verify_ssl=not git_ssl_no_verify) as client:
            merged_prs = client.get_merged_pull_requests(owner, repo, base_branch)
    except Exception as e:
        log.error("failed_to_fetch_merged_prs", error=str(e))
        if warn:
            warn(f"Failed to fetch merged PRs from GitHub: {e}")
        return []

    local_branches = git.get_local_branches(repo_path)
    current_branch = git.get_current_branch(repo_path)

    squash_merged: list[str] = []
    for branch in local_branches:
        if branch in (base_branch, current_branch):
            continue

        if branch not in merged_prs:
            continue

        pr_head_sha = merged_prs[branch]
        if not pr_head_sha:
            log.warning("no_pr_head_sha", branch=branch)
            continue

        local_branch_sha = git.get_branch_sha(repo_path, branch)
        if not local_branch_sha:
            log.warning("no_local_branch_sha", branch=branch)
            continue

        if local_branch_sha == pr_head_sha:
            squash_merged.append(branch)
            log.debug("branch_matches_pr", branch=branch, sha=local_branch_sha)
        elif git.is_ancestor(repo_path, local_branch_sha, pr_head_sha):
            squash_merged.append(branch)
            log.debug("branch_is_older", branch=branch, local_sha=local_branch_sha, pr_sha=pr_head_sha)
        elif git.is_ancestor(repo_path, pr_head_sha, local_branch_sha):
            log.info("branch_has_new_commits", branch=branch, pr_sha=pr_head_sha, local_sha=local_branch_sha)
        else:
            log.info("branch_diverged", branch=branch, pr_sha=pr_head_sha, local_sha=local_branch_sha)

    log.info("found_squash_merged_branches", count=len(squash_merged))
    return squash_merged

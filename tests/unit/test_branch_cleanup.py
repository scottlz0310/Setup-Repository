"""Tests for branch cleanup helpers."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from setup_repo.core.branch_cleanup import get_squash_merged_branches
from setup_repo.core.git import GitOperations


def test_get_squash_merged_branches_no_remote_url() -> None:
    git = MagicMock(spec=GitOperations)
    git.get_remote_url.return_value = None
    warn = MagicMock()

    result = get_squash_merged_branches(
        git,
        Path("repo"),
        "main",
        github_token="token",
        git_ssl_no_verify=False,
        warn=warn,
    )

    assert result == []
    warn.assert_called_once_with("Could not detect GitHub repository from remote URL")
    git.parse_github_repo.assert_not_called()


def test_get_squash_merged_branches_not_github_remote() -> None:
    git = MagicMock(spec=GitOperations)
    git.get_remote_url.return_value = "https://example.com/owner/repo.git"
    git.parse_github_repo.return_value = None
    warn = MagicMock()

    result = get_squash_merged_branches(
        git,
        Path("repo"),
        "main",
        github_token="token",
        git_ssl_no_verify=False,
        warn=warn,
    )

    assert result == []
    warn.assert_called_once_with("Remote URL is not a GitHub repository")


def test_get_squash_merged_branches_missing_token() -> None:
    git = MagicMock(spec=GitOperations)
    git.get_remote_url.return_value = "https://github.com/owner/repo.git"
    git.parse_github_repo.return_value = ("owner", "repo")
    warn = MagicMock()

    result = get_squash_merged_branches(
        git,
        Path("repo"),
        "main",
        github_token=None,
        git_ssl_no_verify=False,
        warn=warn,
    )

    assert result == []
    warn.assert_called_once_with("GitHub token not found. Set SETUP_REPO_GITHUB_TOKEN or run 'setup-repo init'")


def test_get_squash_merged_branches_github_error() -> None:
    git = MagicMock(spec=GitOperations)
    git.get_remote_url.return_value = "https://github.com/owner/repo.git"
    git.parse_github_repo.return_value = ("owner", "repo")
    warn = MagicMock()

    mock_client = MagicMock()
    mock_client.get_merged_pull_requests.side_effect = Exception("boom")
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_client
    mock_context.__exit__.return_value = None

    with patch("setup_repo.core.branch_cleanup.GitHubClient", return_value=mock_context):
        result = get_squash_merged_branches(
            git,
            Path("repo"),
            "main",
            github_token="token",
            git_ssl_no_verify=False,
            warn=warn,
        )

    assert result == []
    warn.assert_called_once_with("Failed to fetch merged PRs from GitHub: boom")


def test_get_squash_merged_branches_matching_rules() -> None:
    git = MagicMock(spec=GitOperations)
    git.get_remote_url.return_value = "https://github.com/owner/repo.git"
    git.parse_github_repo.return_value = ("owner", "repo")
    git.get_local_branches.return_value = [
        "main",
        "develop",
        "feat-eq",
        "feat-old",
        "feat-newer",
        "feat-diverged",
        "feat-not-in-pr",
        "feat-missing-sha",
        "feat-no-pr-sha",
    ]
    git.get_current_branch.return_value = "develop"

    merged_prs = {
        "feat-eq": "sha1",
        "feat-old": "sha2",
        "feat-newer": "sha3",
        "feat-diverged": "sha4",
        "feat-no-pr-sha": None,
        "feat-missing-sha": "sha5",
    }

    def branch_sha(repo_path: Path, branch: str) -> str | None:
        return {
            "feat-eq": "sha1",
            "feat-old": "sha-old",
            "feat-newer": "sha-new",
            "feat-diverged": "sha-div",
            "feat-missing-sha": None,
        }.get(branch)

    def is_ancestor(repo_path: Path, ancestor_sha: str, descendant_ref: str) -> bool:
        return (ancestor_sha, descendant_ref) == ("sha-old", "sha2") or (
            ancestor_sha,
            descendant_ref,
        ) == ("sha3", "sha-new")

    git.get_branch_sha.side_effect = branch_sha
    git.is_ancestor.side_effect = is_ancestor

    mock_client = MagicMock()
    mock_client.get_merged_pull_requests.return_value = merged_prs
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_client
    mock_context.__exit__.return_value = None

    with patch("setup_repo.core.branch_cleanup.GitHubClient", return_value=mock_context) as mock_client_cls:
        result = get_squash_merged_branches(
            git,
            Path("repo"),
            "main",
            github_token="token",
            git_ssl_no_verify=True,
            warn=None,
        )

    assert result == ["feat-eq", "feat-old"]
    mock_client_cls.assert_called_once_with(token="token", verify_ssl=False)

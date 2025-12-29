"""Tests for Pydantic models."""

from datetime import datetime

from setup_repo.models.repository import Repository
from setup_repo.models.result import ProcessResult, ResultStatus, SyncSummary


class TestRepository:
    """Tests for Repository model."""

    def test_repository_creation(self) -> None:
        """Test basic repository creation."""
        repo = Repository(
            name="test-repo",
            full_name="user/test-repo",
            clone_url="https://github.com/user/test-repo.git",
            ssh_url="git@github.com:user/test-repo.git",
        )

        assert repo.name == "test-repo"
        assert repo.full_name == "user/test-repo"
        assert repo.default_branch == "main"
        assert repo.private is False
        assert repo.archived is False
        assert repo.fork is False

    def test_repository_with_custom_values(self) -> None:
        """Test repository with custom values."""
        repo = Repository(
            name="private-repo",
            full_name="user/private-repo",
            clone_url="https://github.com/user/private-repo.git",
            ssh_url="git@github.com:user/private-repo.git",
            default_branch="develop",
            private=True,
            archived=True,
            fork=True,
            pushed_at=datetime(2024, 1, 15, 12, 0, 0),
        )

        assert repo.default_branch == "develop"
        assert repo.private is True
        assert repo.archived is True
        assert repo.fork is True
        assert repo.pushed_at == datetime(2024, 1, 15, 12, 0, 0)

    def test_get_clone_url_ssh(self) -> None:
        """Test get_clone_url returns SSH URL by default."""
        repo = Repository(
            name="test-repo",
            full_name="user/test-repo",
            clone_url="https://github.com/user/test-repo.git",
            ssh_url="git@github.com:user/test-repo.git",
        )

        assert repo.get_clone_url() == "git@github.com:user/test-repo.git"

    def test_get_clone_url_https(self) -> None:
        """Test get_clone_url returns HTTPS URL when requested."""
        repo = Repository(
            name="test-repo",
            full_name="user/test-repo",
            clone_url="https://github.com/user/test-repo.git",
            ssh_url="git@github.com:user/test-repo.git",
        )

        assert repo.get_clone_url(use_https=True) == "https://github.com/user/test-repo.git"


class TestResultStatus:
    """Tests for ResultStatus enum."""

    def test_result_status_values(self) -> None:
        """Test ResultStatus enum values."""
        assert ResultStatus.SUCCESS.value == "success"
        assert ResultStatus.FAILED.value == "failed"
        assert ResultStatus.SKIPPED.value == "skipped"


class TestProcessResult:
    """Tests for ProcessResult model."""

    def test_process_result_creation(self) -> None:
        """Test basic ProcessResult creation."""
        result = ProcessResult(
            repo_name="test-repo",
            status=ResultStatus.SUCCESS,
        )

        assert result.repo_name == "test-repo"
        assert result.status == ResultStatus.SUCCESS
        assert result.duration == 0.0
        assert result.message == ""
        assert result.error is None
        assert result.timestamp is not None

    def test_process_result_with_details(self) -> None:
        """Test ProcessResult with full details."""
        result = ProcessResult(
            repo_name="test-repo",
            status=ResultStatus.FAILED,
            duration=1.5,
            message="Clone failed",
            error="Permission denied",
        )

        assert result.duration == 1.5
        assert result.message == "Clone failed"
        assert result.error == "Permission denied"

    def test_is_success_property(self) -> None:
        """Test is_success property."""
        success = ProcessResult(
            repo_name="repo1",
            status=ResultStatus.SUCCESS,
        )
        failed = ProcessResult(
            repo_name="repo2",
            status=ResultStatus.FAILED,
        )
        skipped = ProcessResult(
            repo_name="repo3",
            status=ResultStatus.SKIPPED,
        )

        assert success.is_success is True
        assert failed.is_success is False
        assert skipped.is_success is False


class TestSyncSummary:
    """Tests for SyncSummary model."""

    def test_sync_summary_from_results(self) -> None:
        """Test SyncSummary.from_results."""
        results = [
            ProcessResult(repo_name="repo1", status=ResultStatus.SUCCESS),
            ProcessResult(repo_name="repo2", status=ResultStatus.SUCCESS),
            ProcessResult(repo_name="repo3", status=ResultStatus.FAILED),
            ProcessResult(repo_name="repo4", status=ResultStatus.SKIPPED),
        ]

        summary = SyncSummary.from_results(results, duration=10.5)

        assert summary.total == 4
        assert summary.success == 2
        assert summary.failed == 1
        assert summary.skipped == 1
        assert summary.duration == 10.5
        assert len(summary.results) == 4

    def test_sync_summary_empty_results(self) -> None:
        """Test SyncSummary with empty results."""
        summary = SyncSummary.from_results([], duration=0.0)

        assert summary.total == 0
        assert summary.success == 0
        assert summary.failed == 0
        assert summary.skipped == 0

"""Tests for parallel processing."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from setup_repo.core.parallel import ParallelProcessor
from setup_repo.models.result import ProcessResult, ResultStatus


class TestParallelProcessor:
    """Tests for ParallelProcessor class."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        processor = ParallelProcessor()
        assert processor.max_workers == 10

    def test_init_custom_workers(self) -> None:
        """Test custom max_workers."""
        processor = ParallelProcessor(max_workers=5)
        assert processor.max_workers == 5

    @patch("setup_repo.core.parallel.Progress")
    def test_process_single_item(self, mock_progress: MagicMock, tmp_path: Path) -> None:
        """Test processing a single item."""
        # Setup mock progress
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress.return_value.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task.return_value = 1

        def process_func(path: Path) -> ProcessResult:
            return ProcessResult(
                repo_name=path.name,
                status=ResultStatus.SUCCESS,
                message="Done",
            )

        processor = ParallelProcessor(max_workers=2)
        items = [tmp_path / "repo1"]

        summary = processor.process(items, process_func, desc="Test")

        assert summary.total == 1
        assert summary.success == 1
        assert summary.failed == 0

    @patch("setup_repo.core.parallel.Progress")
    def test_process_multiple_items(self, mock_progress: MagicMock, tmp_path: Path) -> None:
        """Test processing multiple items."""
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress.return_value.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task.return_value = 1

        def process_func(path: Path) -> ProcessResult:
            return ProcessResult(
                repo_name=path.name,
                status=ResultStatus.SUCCESS,
            )

        processor = ParallelProcessor(max_workers=4)
        items = [tmp_path / f"repo{i}" for i in range(5)]

        summary = processor.process(items, process_func)

        assert summary.total == 5
        assert summary.success == 5

    @patch("setup_repo.core.parallel.Progress")
    def test_process_with_failures(self, mock_progress: MagicMock, tmp_path: Path) -> None:
        """Test processing with some failures."""
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress.return_value.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task.return_value = 1

        def process_func(path: Path) -> ProcessResult:
            if "fail" in path.name:
                return ProcessResult(
                    repo_name=path.name,
                    status=ResultStatus.FAILED,
                    error="Simulated failure",
                )
            return ProcessResult(
                repo_name=path.name,
                status=ResultStatus.SUCCESS,
            )

        processor = ParallelProcessor()
        items = [
            tmp_path / "repo1",
            tmp_path / "fail-repo",
            tmp_path / "repo2",
        ]

        summary = processor.process(items, process_func)

        assert summary.total == 3
        assert summary.success == 2
        assert summary.failed == 1

    @patch("setup_repo.core.parallel.Progress")
    def test_process_handles_exceptions(self, mock_progress: MagicMock, tmp_path: Path) -> None:
        """Test that exceptions are handled gracefully."""
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress.return_value.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task.return_value = 1

        def process_func(path: Path) -> ProcessResult:
            if "error" in path.name:
                raise RuntimeError("Unexpected error")
            return ProcessResult(
                repo_name=path.name,
                status=ResultStatus.SUCCESS,
            )

        processor = ParallelProcessor()
        items = [
            tmp_path / "repo1",
            tmp_path / "error-repo",
        ]

        summary = processor.process(items, process_func)

        assert summary.total == 2
        assert summary.success == 1
        assert summary.failed == 1

    @patch("setup_repo.core.parallel.Progress")
    def test_process_empty_items(self, mock_progress: MagicMock) -> None:
        """Test processing empty list."""
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress.return_value.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task.return_value = 1

        def process_func(path: Path) -> ProcessResult:
            return ProcessResult(
                repo_name=path.name,
                status=ResultStatus.SUCCESS,
            )

        processor = ParallelProcessor()
        summary = processor.process([], process_func)

        assert summary.total == 0
        assert summary.duration >= 0

    @patch("setup_repo.core.parallel.Progress")
    def test_process_records_duration(self, mock_progress: MagicMock, tmp_path: Path) -> None:
        """Test that duration is recorded."""
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__ = MagicMock(return_value=mock_progress_instance)
        mock_progress.return_value.__exit__ = MagicMock(return_value=False)
        mock_progress_instance.add_task.return_value = 1

        def process_func(path: Path) -> ProcessResult:
            return ProcessResult(
                repo_name=path.name,
                status=ResultStatus.SUCCESS,
            )

        processor = ParallelProcessor()
        items = [tmp_path / "repo1"]

        summary = processor.process(items, process_func)

        assert summary.duration >= 0
        # Check that individual result has duration set
        assert len(summary.results) == 1
        assert summary.results[0].duration >= 0

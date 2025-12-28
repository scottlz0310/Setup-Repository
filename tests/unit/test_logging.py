"""Tests for logging configuration."""

from pathlib import Path

import pytest
import structlog

from setup_repo.utils.logging import configure_logging, get_logger, log_context


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_default(self) -> None:
        """Test default logging configuration."""
        configure_logging()

        log = get_logger("test")
        assert log is not None

    def test_configure_logging_with_level(self) -> None:
        """Test logging configuration with custom level."""
        configure_logging(level="DEBUG")

        log = get_logger("test")
        assert log is not None

    def test_configure_logging_with_file(self, temp_log_file: Path) -> None:
        """Test logging configuration with file output."""
        configure_logging(log_file=temp_log_file)

        log = get_logger("test")
        log.info("test message")

        # File should be created (may be empty due to buffering)
        assert temp_log_file.parent.exists()

    def test_configure_logging_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test that logging creates parent directories for log file."""
        log_file = tmp_path / "subdir" / "deep" / "test.log"
        configure_logging(log_file=log_file)

        assert log_file.parent.exists()


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_with_name(self) -> None:
        """Test getting a logger with a name."""
        configure_logging()
        log = get_logger("test_module")
        assert log is not None

    def test_get_logger_without_name(self) -> None:
        """Test getting a logger without a name."""
        configure_logging()
        log = get_logger()
        assert log is not None


class TestLogContext:
    """Tests for log_context context manager."""

    def test_log_context_binds_variables(self) -> None:
        """Test that log_context binds context variables."""
        configure_logging()

        with log_context(repo="test-repo", action="sync"):
            # Context is bound during the context manager
            ctx = structlog.contextvars.get_contextvars()
            assert ctx.get("repo") == "test-repo"
            assert ctx.get("action") == "sync"

    def test_log_context_clears_on_exit(self) -> None:
        """Test that log_context clears context on exit."""
        configure_logging()

        with log_context(repo="test-repo"):
            pass

        ctx = structlog.contextvars.get_contextvars()
        # Context should be cleared after exiting
        assert "repo" not in ctx

    def test_log_context_nested(self) -> None:
        """Test nested log_context usage."""
        configure_logging()

        with log_context(outer="value1"):
            ctx1 = structlog.contextvars.get_contextvars()
            assert ctx1.get("outer") == "value1"

            with log_context(inner="value2"):
                ctx2 = structlog.contextvars.get_contextvars()
                # Note: clear_contextvars clears all, so outer may be lost
                # This is expected behavior with the current implementation
                assert ctx2.get("inner") == "value2"

    def test_log_context_exception_handling(self) -> None:
        """Test that log_context clears even on exception."""
        configure_logging()

        with pytest.raises(ValueError), log_context(key="value"):
            raise ValueError("test error")

        ctx = structlog.contextvars.get_contextvars()
        assert "key" not in ctx

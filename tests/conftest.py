"""Shared pytest fixtures for Setup Repository tests."""

from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def temp_log_file(tmp_path: Path) -> Path:
    """Return a temporary log file path."""
    return tmp_path / "test.log"


@pytest.fixture(autouse=True)
def reset_structlog() -> Generator[None, None, None]:
    """Reset structlog configuration after each test."""
    import structlog

    yield
    structlog.reset_defaults()

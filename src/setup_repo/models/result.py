"""Result models for repository operations."""

from datetime import datetime
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field


class ResultStatus(str, Enum):
    """Status of a repository operation."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProcessResult(BaseModel):
    """Result of processing a single repository."""

    repo_name: str
    status: ResultStatus
    duration: float = 0.0
    message: str = ""
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def is_success(self) -> bool:
        """Check if the result is successful."""
        return self.status == ResultStatus.SUCCESS


class SyncSummary(BaseModel):
    """Summary of a sync operation."""

    total: int
    success: int
    failed: int
    skipped: int
    duration: float
    results: list[ProcessResult]

    @classmethod
    def from_results(
        cls,
        results: list[ProcessResult],
        duration: float,
    ) -> Self:
        """Create a summary from a list of results.

        Args:
            results: List of ProcessResult objects
            duration: Total duration in seconds

        Returns:
            SyncSummary instance
        """
        return cls(
            total=len(results),
            success=sum(1 for r in results if r.status == ResultStatus.SUCCESS),
            failed=sum(1 for r in results if r.status == ResultStatus.FAILED),
            skipped=sum(1 for r in results if r.status == ResultStatus.SKIPPED),
            duration=duration,
            results=results,
        )

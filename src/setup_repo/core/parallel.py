"""Parallel processing with Rich progress."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from setup_repo.models.result import ProcessResult, ResultStatus, SyncSummary
from setup_repo.utils.console import console
from setup_repo.utils.logging import get_logger, log_context

log = get_logger(__name__)


class ParallelProcessor:
    """Parallel processing with progress display."""

    def __init__(self, max_workers: int = 10) -> None:
        """Initialize the processor.

        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers

    def process(
        self,
        items: list[Path],
        process_func: Callable[[Path], ProcessResult],
        desc: str = "Processing",
    ) -> SyncSummary:
        """Process multiple items in parallel.

        Args:
            items: List of paths to process
            process_func: Function to apply to each item
            desc: Description for progress bar

        Returns:
            SyncSummary with all results
        """
        results: list[ProcessResult] = []
        start_time = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(desc, total=len(items))

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._safe_process, item, process_func): item
                    for item in items
                }

                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                        progress.update(
                            task,
                            advance=1,
                            description=f"{desc}: {result.repo_name}",
                        )
                    except Exception as e:
                        log.exception("unexpected_error", item=str(item))
                        results.append(
                            ProcessResult(
                                repo_name=item.name,
                                status=ResultStatus.FAILED,
                                error=str(e),
                            )
                        )
                        progress.update(task, advance=1)

        duration = time.time() - start_time
        return SyncSummary.from_results(results, duration)

    def _safe_process(
        self,
        item: Path,
        func: Callable[[Path], ProcessResult],
    ) -> ProcessResult:
        """Safely process an item with exception handling.

        Args:
            item: Path to process
            func: Processing function

        Returns:
            ProcessResult
        """
        with log_context(repo=item.name):
            start = time.time()
            try:
                result = func(item)
                result.duration = time.time() - start
                return result
            except Exception as e:
                log.exception("process_failed")
                return ProcessResult(
                    repo_name=item.name,
                    status=ResultStatus.FAILED,
                    duration=time.time() - start,
                    error=str(e),
                )

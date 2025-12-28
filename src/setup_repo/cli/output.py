"""Rich output helpers for CLI."""

from rich.panel import Panel
from rich.table import Table

from setup_repo.models.result import ResultStatus, SyncSummary
from setup_repo.utils.console import console


def show_summary(summary: SyncSummary) -> None:
    """Display a sync summary.

    Args:
        summary: SyncSummary to display
    """
    # Summary panel
    console.print(
        Panel(
            f"[green]✓ Success: {summary.success}[/]  "
            f"[red]✗ Failed: {summary.failed}[/]  "
            f"[yellow]⊘ Skipped: {summary.skipped}[/]  "
            f"[dim]Duration: {summary.duration:.1f}s[/]",
            title="Summary",
            border_style="blue",
        )
    )

    # Failed details
    if summary.failed > 0:
        table = Table(title="Failed Repositories", show_header=True)
        table.add_column("Repository", style="cyan")
        table.add_column("Error", style="red")
        table.add_column("Duration", style="dim", justify="right")

        for r in summary.results:
            if r.status == ResultStatus.FAILED:
                table.add_row(
                    r.repo_name,
                    r.error or r.message,
                    f"{r.duration:.1f}s",
                )

        console.print(table)


def show_error(message: str) -> None:
    """Display an error message.

    Args:
        message: Error message to display
    """
    console.print(f"[red]Error:[/] {message}")


def show_warning(message: str) -> None:
    """Display a warning message.

    Args:
        message: Warning message to display
    """
    console.print(f"[yellow]Warning:[/] {message}")


def show_success(message: str) -> None:
    """Display a success message.

    Args:
        message: Success message to display
    """
    console.print(f"[green]✓[/] {message}")


def show_info(message: str) -> None:
    """Display an info message.

    Args:
        message: Info message to display
    """
    console.print(f"[blue]ℹ[/] {message}")

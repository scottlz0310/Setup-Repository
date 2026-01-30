"""Configuration summary display for init command."""

from pathlib import Path

from rich.table import Table

from setup_repo.utils.console import console


def show_summary(
    *,
    github_owner: str,
    github_token: str | None,
    workspace_dir: Path,
    max_workers: int,
    use_https: bool,
    ssl_no_verify: bool,
    log_enabled: bool,
    log_file: Path | None,
    auto_prune: bool,
    auto_stash: bool,
    auto_cleanup: bool,
    auto_cleanup_include_squash: bool,
) -> None:
    """Display configuration summary.

    Args:
        github_owner: GitHub owner name
        github_token: GitHub token (optional)
        workspace_dir: Workspace directory path
        max_workers: Number of parallel workers
        use_https: Whether to use HTTPS for cloning
        ssl_no_verify: Whether to skip SSL verification
        log_enabled: Whether logging is enabled
        log_file: Log file path (if enabled)
        auto_prune: Whether auto prune is enabled
        auto_stash: Whether auto stash is enabled
        auto_cleanup: Whether auto cleanup is enabled
        auto_cleanup_include_squash: Whether to include squash-merged branches
    """
    table = Table(title="Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="dim")
    table.add_column("Value")

    # GitHub
    table.add_row("GitHub Owner", f"[cyan]{github_owner}[/]")
    token_display = "[green]configured[/]" if github_token else "[yellow]not set[/]"
    table.add_row("GitHub Token", token_display)

    # Workspace
    table.add_row("Workspace Dir", str(workspace_dir))
    table.add_row("Parallel Workers", str(max_workers))

    # Git
    table.add_row("Clone Method", "HTTPS" if use_https else "SSH")
    table.add_row("SSL Verify", "[red]disabled[/]" if ssl_no_verify else "[green]enabled[/]")

    # Advanced
    table.add_row("Auto Prune", "[green]enabled[/]" if auto_prune else "[dim]disabled[/]")
    table.add_row("Auto Stash", "[green]enabled[/]" if auto_stash else "[dim]disabled[/]")
    table.add_row("Auto Cleanup", "[green]enabled[/]" if auto_cleanup else "[dim]disabled[/]")
    table.add_row(
        "Auto Cleanup (Squash)",
        "[green]enabled[/]" if auto_cleanup_include_squash else "[dim]disabled[/]",
    )
    if log_enabled and log_file:
        table.add_row("Log File", str(log_file))
    else:
        table.add_row("File Logging", "[dim]disabled[/]")

    console.print(table)

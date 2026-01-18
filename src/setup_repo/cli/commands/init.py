"""Init command for CLI - Interactive setup wizard."""

from pathlib import Path

import typer
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from setup_repo.cli.output import show_error, show_info, show_success, show_warning
from setup_repo.models.config import AppSettings, get_config_path, save_config
from setup_repo.utils.console import console


def init() -> None:
    """Interactive setup wizard for configuration."""
    console.print(
        Panel.fit(
            "[bold cyan]Setup Repository - Configuration Wizard[/]\n"
            "[dim]This wizard will help you configure setup-repo[/]",
            border_style="cyan",
        )
    )
    console.print()

    # Load current/default settings for auto-detection
    settings = AppSettings()

    # Step 1: GitHub Authentication
    console.rule("[bold]Step 1: GitHub Authentication[/]")
    github_owner, github_token = _configure_github(settings)

    # Step 2: Workspace Settings
    console.rule("[bold]Step 2: Workspace Settings[/]")
    workspace_dir, max_workers = _configure_workspace(settings)

    # Step 3: Git Settings
    console.rule("[bold]Step 3: Git Settings[/]")
    use_https, ssl_no_verify = _configure_git(settings, github_token)

    # Step 4: Advanced Options
    console.rule("[bold]Step 4: Advanced Options[/]")
    log_enabled, log_file, auto_prune, auto_stash, auto_cleanup = _configure_advanced()

    # Show summary and confirm
    console.rule("[bold]Configuration Summary[/]")
    _show_summary(
        github_owner=github_owner,
        github_token=github_token,
        workspace_dir=workspace_dir,
        max_workers=max_workers,
        use_https=use_https,
        ssl_no_verify=ssl_no_verify,
        log_enabled=log_enabled,
        log_file=log_file,
        auto_prune=auto_prune,
        auto_stash=auto_stash,
        auto_cleanup=auto_cleanup,
    )

    console.print()
    if not Confirm.ask("[bold]Save this configuration?[/]", default=True):
        show_warning("Configuration cancelled")
        raise typer.Exit(0)

    # Save configuration
    config_path = get_config_path()
    try:
        save_config(
            config_path,
            github_owner=github_owner,
            github_token=github_token,
            workspace_dir=workspace_dir,
            max_workers=max_workers,
            use_https=use_https,
            git_ssl_no_verify=ssl_no_verify,
            log_file=log_file if log_enabled else None,
            auto_prune=auto_prune,
            auto_stash=auto_stash,
            auto_cleanup=auto_cleanup,
        )
        show_success(f"Configuration saved to [cyan]{config_path}[/]")
    except OSError as e:
        show_error(f"Failed to save configuration: {e}")
        raise typer.Exit(1) from e


def _configure_github(settings: AppSettings) -> tuple[str, str | None]:
    """Configure GitHub settings."""
    # GitHub Owner
    detected_owner = settings.github_owner
    if detected_owner:
        show_info(f"Detected GitHub owner: [cyan]{detected_owner}[/]")
        if Confirm.ask("Use this owner?", default=True):
            github_owner = detected_owner
        else:
            github_owner = Prompt.ask("Enter GitHub owner (username or organization)")
    else:
        show_warning("Could not auto-detect GitHub owner")
        github_owner = Prompt.ask("Enter GitHub owner (username or organization)")

    # GitHub Token
    detected_token = settings.github_token
    if detected_token:
        masked = detected_token[:4] + "..." + detected_token[-4:] if len(detected_token) > 8 else "****"
        show_info(f"Detected GitHub token: [dim]{masked}[/]")
        if Confirm.ask("Use this token?", default=True):
            github_token = detected_token
        else:
            github_token = Prompt.ask("Enter GitHub token (or leave empty)", default="", password=True) or None
    else:
        show_warning("Could not auto-detect GitHub token (run 'gh auth login' to set up)")
        github_token = Prompt.ask("Enter GitHub token (or leave empty)", default="", password=True) or None

    return github_owner, github_token


def _configure_workspace(settings: AppSettings) -> tuple[Path, int]:
    """Configure workspace settings."""
    # Workspace directory
    default_dir = settings.workspace_dir
    show_info(f"Default workspace directory: [cyan]{default_dir}[/]")

    if Confirm.ask("Use this directory?", default=True):
        workspace_dir = default_dir
    else:
        workspace_str = Prompt.ask("Enter workspace directory", default=str(default_dir))
        workspace_dir = Path(workspace_str).expanduser().resolve()

    # Max workers
    default_workers = settings.max_workers
    show_info(f"Default parallel workers: [cyan]{default_workers}[/]")

    if Confirm.ask("Use this setting?", default=True):
        max_workers = default_workers
    else:
        max_workers = int(Prompt.ask("Enter number of parallel workers", default=str(default_workers)))

    return workspace_dir, max_workers


def _configure_git(settings: AppSettings, github_token: str | None) -> tuple[bool, bool]:
    """Configure Git settings and validate."""
    console.print("\n[bold]Clone method:[/]")
    console.print("  [cyan]1.[/] HTTPS (recommended if you have a token)")
    console.print("  [cyan]2.[/] SSH (requires SSH key setup)")

    choice = Prompt.ask("Select clone method", choices=["1", "2"], default="1")
    use_https = choice == "1"

    # Validate the choice
    if use_https and not github_token:
        show_warning("HTTPS without token may limit API access to public repos only")
    elif not use_https:
        # Check SSH key
        ssh_key = Path.home() / ".ssh" / "id_rsa"
        ssh_key_ed = Path.home() / ".ssh" / "id_ed25519"
        if not ssh_key.exists() and not ssh_key_ed.exists():
            show_warning("No SSH key found (~/.ssh/id_rsa or id_ed25519)")
            show_info("Run 'ssh-keygen' to create one, then add to GitHub")

    if use_https:
        show_success("HTTPS clone will be used")
    else:
        show_success("SSH clone will be used")

    # SSL verification
    ssl_no_verify = False
    if use_https:
        console.print()
        show_info("SSL verification is enabled by default")
        if Confirm.ask("Disable SSL verification? (for corporate proxies)", default=False):
            ssl_no_verify = True
            show_warning("SSL verification will be disabled")

    return use_https, ssl_no_verify


def _configure_advanced() -> tuple[bool, Path | None, bool, bool, bool]:
    """Configure advanced options."""
    # Logging
    log_enabled = Confirm.ask("Enable file logging?", default=False)
    log_file: Path | None = None

    if log_enabled:
        default_log = Path.home() / ".local" / "share" / "setup-repo" / "logs" / "setup-repo.jsonl"
        show_info(f"Default log path: [dim]{default_log}[/]")

        if Confirm.ask("Use this path?", default=True):
            log_file = default_log
        else:
            log_str = Prompt.ask("Enter log file path", default=str(default_log))
            log_file = Path(log_str).expanduser().resolve()

        show_success(f"Logs will be saved to: [cyan]{log_file}[/]")

    # Auto prune
    console.print()
    show_info("Auto prune: Remove remote-tracking references that no longer exist")
    auto_prune = Confirm.ask("Enable auto prune on pull?", default=True)

    # Auto stash
    show_info("Auto stash: Automatically stash/unstash uncommitted changes on pull")
    auto_stash = Confirm.ask("Enable auto stash on pull?", default=False)

    show_info("Auto cleanup: Remove merged branches after sync")
    auto_cleanup = Confirm.ask("Enable auto cleanup after sync?", default=False)

    return log_enabled, log_file, auto_prune, auto_stash, auto_cleanup


def _show_summary(
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
) -> None:
    """Display configuration summary."""
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
    if log_enabled and log_file:
        table.add_row("Log File", str(log_file))
    else:
        table.add_row("File Logging", "[dim]disabled[/]")

    console.print(table)


def configure_github(settings: AppSettings) -> tuple[str, str | None]:
    """Public wrapper for GitHub configuration."""
    return _configure_github(settings)


def configure_workspace(settings: AppSettings) -> tuple[Path, int]:
    """Public wrapper for workspace configuration."""
    return _configure_workspace(settings)


def configure_git(settings: AppSettings, github_token: str | None) -> tuple[bool, bool]:
    """Public wrapper for Git configuration."""
    return _configure_git(settings, github_token)


def configure_advanced() -> tuple[bool, Path | None, bool, bool, bool]:
    """Public wrapper for advanced configuration."""
    return _configure_advanced()


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
) -> None:
    """Public wrapper for summary output."""
    _show_summary(
        github_owner=github_owner,
        github_token=github_token,
        workspace_dir=workspace_dir,
        max_workers=max_workers,
        use_https=use_https,
        ssl_no_verify=ssl_no_verify,
        log_enabled=log_enabled,
        log_file=log_file,
        auto_prune=auto_prune,
        auto_stash=auto_stash,
        auto_cleanup=auto_cleanup,
    )

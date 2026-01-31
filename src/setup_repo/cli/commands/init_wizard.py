"""Configuration wizard steps for init command."""

from pathlib import Path

from rich.prompt import Confirm, Prompt

from setup_repo.cli.output import show_info, show_success, show_warning
from setup_repo.models.config import AppSettings
from setup_repo.utils.console import console


def configure_github(settings: AppSettings, interactive: bool = True) -> tuple[str, str | None]:
    """Configure GitHub settings.

    Args:
        settings: Application settings with auto-detected values

    Returns:
        Tuple of (github_owner, github_token)
    """
    # GitHub Owner
    detected_owner = settings.github_owner
    if detected_owner:
        show_info(f"Detected GitHub owner: [cyan]{detected_owner}[/]")
        if interactive:
            if Confirm.ask("Use this owner?", default=True):
                github_owner = detected_owner
            else:
                github_owner = Prompt.ask("Enter GitHub owner (username or organization)")
        else:
            github_owner = detected_owner
    else:
        show_warning("Could not auto-detect GitHub owner")
        github_owner = Prompt.ask("Enter GitHub owner (username or organization)") if interactive else ""

    # GitHub Token
    detected_token = settings.github_token
    if detected_token:
        masked = detected_token[:4] + "..." + detected_token[-4:] if len(detected_token) > 8 else "****"
        show_info(f"Detected GitHub token: [dim]{masked}[/]")
        if interactive:
            if Confirm.ask("Use this token?", default=True):
                github_token = detected_token
            else:
                github_token = (
                    Prompt.ask(
                        "Enter GitHub token (or leave empty)",
                        default="",
                        password=True,
                    )
                    or None
                )
        else:
            github_token = detected_token
    else:
        show_warning("Could not auto-detect GitHub token (run 'gh auth login' to set up)")
        github_token = (
            (Prompt.ask("Enter GitHub token (or leave empty)", default="", password=True) or None)
            if interactive
            else None
        )

    return github_owner, github_token


def configure_workspace(settings: AppSettings, interactive: bool = True) -> tuple[Path, int]:
    """Configure workspace settings.

    Args:
        settings: Application settings with default values

    Returns:
        Tuple of (workspace_dir, max_workers)
    """
    # Workspace directory
    default_dir = settings.workspace_dir
    show_info(f"Default workspace directory: [cyan]{default_dir}[/]")

    if interactive:
        if Confirm.ask("Use this directory?", default=True):
            workspace_dir = default_dir
        else:
            workspace_str = Prompt.ask("Enter workspace directory", default=str(default_dir))
            workspace_dir = Path(workspace_str).expanduser().resolve()
    else:
        workspace_dir = default_dir

    # Max workers
    default_workers = settings.max_workers
    show_info(f"Default parallel workers: [cyan]{default_workers}[/]")

    if interactive:
        if Confirm.ask("Use this setting?", default=True):
            max_workers = default_workers
        else:
            max_workers = int(Prompt.ask("Enter number of parallel workers", default=str(default_workers)))
    else:
        max_workers = default_workers

    return workspace_dir, max_workers


def configure_advanced(
    settings: AppSettings,
    interactive: bool = True,
) -> tuple[bool, Path | None, bool, bool, bool, bool]:
    """Configure advanced options.

    Returns:
        Tuple of (log_enabled, log_file, auto_prune, auto_stash, auto_cleanup, auto_cleanup_include_squash)
    """
    # Logging
    if interactive:
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
    else:
        log_file = settings.log_file
        log_enabled = log_file is not None

    # Auto prune
    if interactive:
        console.print()
        show_info("Auto prune: Remove remote-tracking references that no longer exist")
        auto_prune = Confirm.ask("Enable auto prune on pull?", default=True)

        # Auto stash
        show_info("Auto stash: Automatically stash/unstash uncommitted changes on pull")
        auto_stash = Confirm.ask("Enable auto stash on pull?", default=False)

        show_info("Auto cleanup: Remove merged branches after sync")
        auto_cleanup = Confirm.ask("Enable auto cleanup after sync?", default=False)

        auto_cleanup_include_squash = False
        if auto_cleanup:
            show_info("Include squash-merged branches (requires GitHub API access)")
            auto_cleanup_include_squash = Confirm.ask(
                "Include squash-merged branches in auto cleanup?",
                default=False,
            )
    else:
        auto_prune = settings.auto_prune
        auto_stash = settings.auto_stash
        auto_cleanup = settings.auto_cleanup
        auto_cleanup_include_squash = settings.auto_cleanup_include_squash

    return log_enabled, log_file, auto_prune, auto_stash, auto_cleanup, auto_cleanup_include_squash

"""Init command for CLI - Interactive setup wizard."""

import typer
from rich.panel import Panel
from rich.prompt import Confirm

from setup_repo.cli.commands.init_display import show_summary
from setup_repo.cli.commands.init_validators import configure_git
from setup_repo.cli.commands.init_wizard import configure_advanced, configure_github, configure_workspace
from setup_repo.cli.output import show_error, show_success, show_warning
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
    github_owner, github_token = configure_github(settings)

    # Step 2: Workspace Settings
    console.rule("[bold]Step 2: Workspace Settings[/]")
    workspace_dir, max_workers = configure_workspace(settings)

    # Step 3: Git Settings
    console.rule("[bold]Step 3: Git Settings[/]")
    use_https, ssl_no_verify = configure_git(settings, github_token)

    # Step 4: Advanced Options
    console.rule("[bold]Step 4: Advanced Options[/]")
    log_enabled, log_file, auto_prune, auto_stash, auto_cleanup, auto_cleanup_include_squash = configure_advanced()

    # Show summary and confirm
    console.rule("[bold]Configuration Summary[/]")
    show_summary(
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
        auto_cleanup_include_squash=auto_cleanup_include_squash,
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
            auto_cleanup_include_squash=auto_cleanup_include_squash,
        )
        show_success(f"Configuration saved to [cyan]{config_path}[/]")
    except OSError as e:
        show_error(f"Failed to save configuration: {e}")
        raise typer.Exit(1) from e

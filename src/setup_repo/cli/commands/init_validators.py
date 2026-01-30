"""Configuration validation for init command."""

from pathlib import Path

from rich.prompt import Confirm, Prompt

from setup_repo.cli.output import show_info, show_success, show_warning
from setup_repo.models.config import AppSettings
from setup_repo.utils.console import console


def configure_git(settings: AppSettings, github_token: str | None, interactive: bool = True) -> tuple[bool, bool]:
    """Configure Git settings and validate.

    Args:
        settings: Application settings
        github_token: GitHub token (for validation)

    Returns:
        Tuple of (use_https, ssl_no_verify)
    """
    console.print("\n[bold]Clone method:[/]")
    console.print("  [cyan]1.[/] HTTPS (recommended if you have a token)")
    console.print("  [cyan]2.[/] SSH (requires SSH key setup)")

    if interactive:
        choice = Prompt.ask("Select clone method", choices=["1", "2"], default="1")
        use_https = choice == "1"
    else:
        use_https = True

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
    if use_https and interactive:
        console.print()
        show_info("SSL verification is enabled by default")
        if Confirm.ask("Disable SSL verification? (for corporate proxies)", default=False):
            ssl_no_verify = True
            show_warning("SSL verification will be disabled")

    return use_https, ssl_no_verify

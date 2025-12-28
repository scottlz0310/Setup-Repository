"""Application settings using Pydantic Settings."""

import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="SETUP_REPO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GitHub settings
    github_owner: str = Field(default="", description="GitHub owner name")
    github_token: str | None = Field(default=None, description="GitHub Token")
    use_https: bool = Field(default=False, description="Use HTTPS for cloning")

    # Directory settings
    workspace_dir: Path = Field(
        default=Path.home() / "workspace",
        description="Directory to clone repositories",
    )

    # Parallel processing settings
    max_workers: int = Field(default=10, ge=1, le=32, description="Number of parallel workers")

    # Git settings
    auto_prune: bool = Field(default=True, description="Auto fetch --prune")
    auto_stash: bool = Field(default=False, description="Auto stash/pop on pull")
    git_ssl_no_verify: bool = Field(default=False, description="Skip SSL verification (for internal CA)")

    # Logging settings
    log_level: str = Field(default="INFO", description="Log level")
    log_file: Path | None = Field(default=None, description="Log file path")

    @model_validator(mode="after")
    def auto_detect_github_settings(self) -> Self:
        """Auto-detect GitHub settings if not provided."""
        # Auto-detect github_owner
        if not self.github_owner:
            if owner := os.environ.get("GITHUB_USER"):
                self.github_owner = owner
            else:
                try:
                    result = subprocess.run(
                        ["git", "config", "user.name"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        self.github_owner = result.stdout.strip()
                except Exception:
                    pass

        # Auto-detect github_token
        if not self.github_token:
            try:
                result = subprocess.run(
                    ["gh", "auth", "token"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    self.github_token = result.stdout.strip()
            except Exception:
                pass

        return self


@lru_cache
def get_settings() -> AppSettings:
    """Get cached application settings.

    Returns:
        Cached AppSettings instance
    """
    return AppSettings()


def reset_settings() -> None:
    """Clear settings cache (for testing)."""
    get_settings.cache_clear()

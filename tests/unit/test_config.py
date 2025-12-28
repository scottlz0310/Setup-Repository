"""Tests for application settings."""

from pathlib import Path
from unittest.mock import patch

import pytest

from setup_repo.models.config import AppSettings, get_settings, reset_settings


class TestAppSettings:
    """Tests for AppSettings class."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = AppSettings(github_owner="test", github_token="token")

        assert settings.use_https is False
        assert settings.max_workers == 10
        assert settings.auto_prune is True
        assert settings.auto_stash is False
        assert settings.git_ssl_no_verify is False
        assert settings.log_level == "INFO"
        assert settings.log_file is None

    def test_workspace_dir_default(self) -> None:
        """Test workspace_dir defaults to ~/workspace."""
        settings = AppSettings(github_owner="test")
        assert settings.workspace_dir == Path.home() / "workspace"

    def test_custom_workspace_dir(self) -> None:
        """Test custom workspace_dir."""
        settings = AppSettings(
            github_owner="test",
            workspace_dir=Path("/custom/path"),
        )
        assert settings.workspace_dir == Path("/custom/path")

    def test_max_workers_validation(self) -> None:
        """Test max_workers validation."""
        # Valid range
        settings = AppSettings(github_owner="test", max_workers=1)
        assert settings.max_workers == 1

        settings = AppSettings(github_owner="test", max_workers=32)
        assert settings.max_workers == 32

        # Out of range
        with pytest.raises(ValueError):
            AppSettings(github_owner="test", max_workers=0)

        with pytest.raises(ValueError):
            AppSettings(github_owner="test", max_workers=33)

    def test_github_owner_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test github_owner from environment variable."""
        monkeypatch.setenv("GITHUB_USER", "env-user")

        settings = AppSettings()
        assert settings.github_owner == "env-user"

    def test_github_owner_explicit_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test explicit github_owner overrides env."""
        monkeypatch.setenv("GITHUB_USER", "env-user")

        settings = AppSettings(github_owner="explicit-user")
        assert settings.github_owner == "explicit-user"

    def test_settings_from_env_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test settings from SETUP_REPO_ prefixed env vars."""
        monkeypatch.setenv("SETUP_REPO_GITHUB_OWNER", "prefix-user")
        monkeypatch.setenv("SETUP_REPO_USE_HTTPS", "true")
        monkeypatch.setenv("SETUP_REPO_MAX_WORKERS", "5")

        settings = AppSettings()
        assert settings.github_owner == "prefix-user"
        assert settings.use_https is True
        assert settings.max_workers == 5

    def test_git_ssl_no_verify(self) -> None:
        """Test git_ssl_no_verify setting."""
        settings = AppSettings(
            github_owner="test",
            git_ssl_no_verify=True,
        )
        assert settings.git_ssl_no_verify is True


class TestGetSettings:
    """Tests for get_settings function."""

    def setup_method(self) -> None:
        """Reset settings cache before each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Reset settings cache after each test."""
        reset_settings()

    def test_get_settings_returns_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that get_settings returns cached instance."""
        monkeypatch.setenv("SETUP_REPO_GITHUB_OWNER", "cached-user")

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reset_settings_clears_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that reset_settings clears the cache."""
        monkeypatch.setenv("SETUP_REPO_GITHUB_OWNER", "user1")

        settings1 = get_settings()
        reset_settings()

        monkeypatch.setenv("SETUP_REPO_GITHUB_OWNER", "user2")
        settings2 = get_settings()

        assert settings1 is not settings2
        assert settings1.github_owner == "user1"
        assert settings2.github_owner == "user2"


class TestAutoDetection:
    """Tests for auto-detection of GitHub settings."""

    def test_auto_detect_github_token_from_gh(self) -> None:
        """Test auto-detection of GitHub token from gh CLI."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "gh_token_12345\n"

            settings = AppSettings(github_owner="test")
            assert settings.github_token == "gh_token_12345"

    def test_auto_detect_fails_gracefully(self) -> None:
        """Test that auto-detection fails gracefully."""
        with patch("subprocess.run", side_effect=Exception("Command failed")):
            # Should not raise, just leave values empty/None
            settings = AppSettings()
            # github_owner might be empty, github_token should be None
            assert settings.github_token is None

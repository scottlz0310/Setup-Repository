"""Tests for application settings."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from setup_repo.models.config import (
    AppSettings,
    get_config_path,
    get_settings,
    load_config_file,
    reset_settings,
    save_config,
)


@pytest.fixture(autouse=True)
def mock_load_config_file(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Ensure tests don't read user's actual config file.

    Tests can skip this by using @pytest.mark.uses_real_config_loader
    """
    if "uses_real_config_loader" in request.keywords:
        yield
        return

    with patch("setup_repo.models.config.load_config_file", return_value={}):
        yield


class TestAppSettings:
    """Tests for AppSettings class."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        settings = AppSettings(github_owner="test", github_token="token")

        assert settings.use_https is False
        assert settings.max_workers == 10
        assert settings.auto_prune is True
        assert settings.auto_stash is False
        assert settings.auto_cleanup is False
        assert settings.auto_cleanup_include_squash is False
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
        with patch("subprocess.run", side_effect=OSError("Command not found")):
            # Should not raise, just leave values empty/None
            settings = AppSettings()
            # github_owner might be empty, github_token should be None
            assert settings.github_token is None


class TestConfigPath:
    """Tests for config path functions."""

    def test_get_config_path(self) -> None:
        """Test get_config_path returns expected path."""
        config_path = get_config_path()
        assert config_path == Path.home() / ".config" / "setup-repo" / "config.toml"

    def test_load_config_file_not_exists(self) -> None:
        """Test load_config_file returns empty dict when file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            config = load_config_file()
            assert config == {}

    def test_load_config_file_valid_toml(self, tmp_path: Path) -> None:
        """Test load_config_file parses valid TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[github]
owner = "test-owner"
token = "test-token"

[workspace]
dir = "/test/workspace"
max_workers = 5

[git]
use_https = true
ssl_no_verify = false
auto_prune = true
auto_stash = false

[logging]
file = "/var/log/setup-repo.jsonl"
level = "DEBUG"
""")
        with patch("setup_repo.models.config.get_config_path", return_value=config_file):
            config = load_config_file()

        assert config["github"]["owner"] == "test-owner"
        assert config["github"]["token"] == "test-token"
        assert config["workspace"]["dir"] == "/test/workspace"
        assert config["workspace"]["max_workers"] == 5
        assert config["git"]["use_https"] is True
        assert config["logging"]["level"] == "DEBUG"

    def test_load_config_file_invalid_toml(self, tmp_path: Path) -> None:
        """Test load_config_file returns empty dict for invalid TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("invalid toml content [[[")

        with patch("setup_repo.models.config.get_config_path", return_value=config_file):
            config = load_config_file()
            assert config == {}


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_creates_file(self, tmp_path: Path) -> None:
        """Test save_config creates config file."""
        config_path = tmp_path / "subdir" / "config.toml"

        save_config(
            config_path,
            github_owner="test-owner",
            github_token="test-token",
            workspace_dir=Path("/test/workspace"),
            max_workers=8,
            use_https=True,
            git_ssl_no_verify=False,
            log_file=Path("/var/log/test.jsonl"),
            auto_prune=True,
            auto_stash=False,
            auto_cleanup=True,
            auto_cleanup_include_squash=True,
        )

        assert config_path.exists()
        content = config_path.read_text()
        assert 'owner = "test-owner"' in content
        assert 'token = "test-token"' in content
        assert 'dir = "/test/workspace"' in content
        assert "max_workers = 8" in content
        assert "use_https = true" in content
        assert "auto_prune = true" in content
        assert "auto_stash = false" in content
        assert "auto_cleanup = true" in content
        assert "auto_cleanup_include_squash = true" in content
        assert 'file = "/var/log/test.jsonl"' in content

    def test_save_config_without_token(self, tmp_path: Path) -> None:
        """Test save_config without token."""
        config_path = tmp_path / "config.toml"

        save_config(
            config_path,
            github_owner="test-owner",
            github_token=None,
            workspace_dir=Path("/test/workspace"),
            max_workers=10,
            use_https=False,
            git_ssl_no_verify=False,
            log_file=None,
            auto_prune=True,
            auto_stash=False,
            auto_cleanup=False,
            auto_cleanup_include_squash=False,
        )

        content = config_path.read_text()
        assert 'owner = "test-owner"' in content
        assert "token" not in content or "# " in content.split("token")[0].split("\n")[-1]

    def test_save_config_without_log_file(self, tmp_path: Path) -> None:
        """Test save_config without log file (commented out)."""
        config_path = tmp_path / "config.toml"

        save_config(
            config_path,
            github_owner="test-owner",
            github_token=None,
            workspace_dir=Path("/test/workspace"),
            max_workers=10,
            use_https=True,
            git_ssl_no_verify=False,
            log_file=None,
            auto_prune=True,
            auto_stash=False,
            auto_cleanup=False,
            auto_cleanup_include_squash=False,
        )

        content = config_path.read_text()
        assert "# file =" in content


@pytest.mark.uses_real_config_loader
class TestAppSettingsWithToml:
    """Tests for AppSettings loading from TOML."""

    def test_settings_from_toml(self, tmp_path: Path) -> None:
        """Test AppSettings loads from TOML file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[github]
owner = "toml-owner"

[workspace]
dir = "/toml/workspace"
max_workers = 15

[git]
use_https = true
auto_stash = true
auto_cleanup = true
auto_cleanup_include_squash = true
""")
        with patch("setup_repo.models.config.get_config_path", return_value=config_file):
            settings = AppSettings()

        assert settings.github_owner == "toml-owner"
        assert settings.workspace_dir == Path("/toml/workspace")
        assert settings.max_workers == 15
        assert settings.use_https is True
        assert settings.auto_stash is True
        assert settings.auto_cleanup is True
        assert settings.auto_cleanup_include_squash is True

    def test_env_overrides_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test environment variables override TOML settings."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[github]
owner = "toml-owner"
""")
        monkeypatch.setenv("SETUP_REPO_GITHUB_OWNER", "env-owner")

        with patch("setup_repo.models.config.get_config_path", return_value=config_file):
            settings = AppSettings()

        # Environment variable takes precedence
        assert settings.github_owner == "env-owner"

"""Tests for init command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from setup_repo.cli.commands.init import init
from setup_repo.cli.commands.init_display import show_summary
from setup_repo.cli.commands.init_validators import configure_git
from setup_repo.cli.commands.init_wizard import configure_advanced, configure_github, configure_workspace
from setup_repo.models.config import AppSettings


class TestConfigureGithub:
    """Tests for configure_github function."""

    def test_uses_detected_owner_when_confirmed(self) -> None:
        """Test using detected GitHub owner when confirmed."""
        settings = MagicMock(spec=AppSettings)
        settings.github_owner = "detected-owner"
        settings.github_token = None

        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = True
            with patch("setup_repo.cli.commands.init_wizard.Prompt") as mock_prompt:
                mock_prompt.ask.return_value = ""

                owner, token = configure_github(settings)

        assert owner == "detected-owner"
        assert token is None

    def test_prompts_for_owner_when_not_confirmed(self) -> None:
        """Test prompting for owner when not using detected value."""
        settings = MagicMock(spec=AppSettings)
        settings.github_owner = "detected-owner"
        settings.github_token = None

        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = False
            with patch("setup_repo.cli.commands.init_wizard.Prompt") as mock_prompt:
                mock_prompt.ask.side_effect = ["custom-owner", ""]

                owner, _ = configure_github(settings)

        assert owner == "custom-owner"

    def test_prompts_for_owner_when_not_detected(self) -> None:
        """Test prompting for owner when not auto-detected."""
        settings = MagicMock(spec=AppSettings)
        settings.github_owner = ""
        settings.github_token = None

        with patch("setup_repo.cli.commands.init_wizard.Prompt") as mock_prompt:
            mock_prompt.ask.side_effect = ["manual-owner", ""]

            owner, _ = configure_github(settings)

        assert owner == "manual-owner"

    def test_uses_detected_token_when_confirmed(self) -> None:
        """Test using detected token when confirmed."""
        settings = MagicMock(spec=AppSettings)
        settings.github_owner = "owner"
        settings.github_token = "ghp_detected123token456"

        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = True

            _, token = configure_github(settings)

        assert token == "ghp_detected123token456"

    def test_prompts_for_token_when_not_confirmed(self) -> None:
        """Test prompting for token when not using detected value."""
        settings = MagicMock(spec=AppSettings)
        settings.github_owner = "owner"
        settings.github_token = "detected-token"

        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.side_effect = [True, False]
            with patch("setup_repo.cli.commands.init_wizard.Prompt") as mock_prompt:
                mock_prompt.ask.return_value = "custom-token"

                _, token = configure_github(settings)

        assert token == "custom-token"

    def test_empty_token_becomes_none(self) -> None:
        """Test that empty token input becomes None."""
        settings = MagicMock(spec=AppSettings)
        settings.github_owner = "owner"
        settings.github_token = "detected"

        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.side_effect = [True, False]
            with patch("setup_repo.cli.commands.init_wizard.Prompt") as mock_prompt:
                mock_prompt.ask.return_value = ""

                _, token = configure_github(settings)

        assert token is None


class TestConfigureWorkspace:
    """Tests for configure_workspace function."""

    def test_uses_default_directory_when_confirmed(self) -> None:
        """Test using default workspace directory when confirmed."""
        settings = MagicMock(spec=AppSettings)
        settings.workspace_dir = Path("/default/workspace")
        settings.max_workers = 10

        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = True

            workspace, workers = configure_workspace(settings)

        assert workspace == Path("/default/workspace")
        assert workers == 10

    def test_prompts_for_directory_when_not_confirmed(self, tmp_path: Path) -> None:
        """Test prompting for directory when not using default."""
        settings = MagicMock(spec=AppSettings)
        settings.workspace_dir = Path("/default/workspace")
        settings.max_workers = 10

        custom_path = str(tmp_path / "custom")

        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.side_effect = [False, True]
            with patch("setup_repo.cli.commands.init_wizard.Prompt") as mock_prompt:
                mock_prompt.ask.return_value = custom_path

                workspace, _ = configure_workspace(settings)

        assert workspace == Path(custom_path)

    def test_custom_max_workers(self) -> None:
        """Test setting custom max workers."""
        settings = MagicMock(spec=AppSettings)
        settings.workspace_dir = Path("/workspace")
        settings.max_workers = 10

        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.side_effect = [True, False]
            with patch("setup_repo.cli.commands.init_wizard.Prompt") as mock_prompt:
                mock_prompt.ask.return_value = "5"

                _, workers = configure_workspace(settings)

        assert workers == 5


class TestConfigureGit:
    """Tests for configure_git function."""

    def test_https_selection(self) -> None:
        """Test selecting HTTPS clone method."""
        settings = MagicMock(spec=AppSettings)

        with patch("setup_repo.cli.commands.init_validators.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "1"
            with patch("setup_repo.cli.commands.init_validators.Confirm") as mock_confirm:
                mock_confirm.ask.return_value = False

                use_https, ssl_no_verify = configure_git(settings, "token")

        assert use_https is True
        assert ssl_no_verify is False

    def test_ssh_selection(self) -> None:
        """Test selecting SSH clone method."""
        settings = MagicMock(spec=AppSettings)

        with patch("setup_repo.cli.commands.init_validators.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "2"

            use_https, ssl_no_verify = configure_git(settings, "token")

        assert use_https is False
        assert ssl_no_verify is False

    def test_https_without_token_warning(self) -> None:
        """Test warning when using HTTPS without token."""
        settings = MagicMock(spec=AppSettings)

        with patch("setup_repo.cli.commands.init_validators.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "1"
            with patch("setup_repo.cli.commands.init_validators.Confirm") as mock_confirm:
                mock_confirm.ask.return_value = False
                with patch("setup_repo.cli.commands.init_validators.show_warning") as mock_warn:
                    configure_git(settings, None)

        mock_warn.assert_called()

    def test_ssl_no_verify_enabled(self) -> None:
        """Test enabling SSL no verify."""
        settings = MagicMock(spec=AppSettings)

        with patch("setup_repo.cli.commands.init_validators.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "1"
            with patch("setup_repo.cli.commands.init_validators.Confirm") as mock_confirm:
                mock_confirm.ask.return_value = True

                _, ssl_no_verify = configure_git(settings, "token")

        assert ssl_no_verify is True

    def test_ssh_no_key_warning(self) -> None:
        """Test warning when SSH selected but no SSH key exists."""
        settings = MagicMock(spec=AppSettings)

        with (
            patch("setup_repo.cli.commands.init_validators.Prompt") as mock_prompt,
            patch("pathlib.Path.exists", return_value=False),
            patch("setup_repo.cli.commands.init_validators.show_warning") as mock_warn,
        ):
            mock_prompt.ask.return_value = "2"
            configure_git(settings, "token")

        mock_warn.assert_called()


class TestConfigureAdvanced:
    """Tests for configure_advanced function."""

    def test_logging_disabled(self) -> None:
        """Test with logging disabled."""
        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.side_effect = [False, True, False, False]

            (
                log_enabled,
                log_file,
                auto_prune,
                auto_stash,
                auto_cleanup,
                auto_cleanup_include_squash,
            ) = configure_advanced()

        assert log_enabled is False
        assert log_file is None
        assert auto_prune is True
        assert auto_stash is False
        assert auto_cleanup is False
        assert auto_cleanup_include_squash is False

    def test_logging_enabled_default_path(self) -> None:
        """Test with logging enabled using default path."""
        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.side_effect = [True, True, True, False, False]

            log_enabled, log_file, _, _, auto_cleanup, auto_cleanup_include_squash = configure_advanced()

        assert log_enabled is True
        assert log_file is not None
        assert "setup-repo.jsonl" in str(log_file)
        assert auto_cleanup is False
        assert auto_cleanup_include_squash is False

    def test_logging_enabled_custom_path(self, tmp_path: Path) -> None:
        """Test with logging enabled using custom path."""
        custom_log = str(tmp_path / "custom" / "log.jsonl")

        with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
            mock_confirm.ask.side_effect = [True, False, True, True, False]
            with patch("setup_repo.cli.commands.init_wizard.Prompt") as mock_prompt:
                mock_prompt.ask.return_value = custom_log

                log_enabled, log_file, _, auto_stash, auto_cleanup, auto_cleanup_include_squash = configure_advanced()

        assert log_enabled is True
        assert log_file == Path(custom_log)
        assert auto_stash is True
        assert auto_cleanup is False
        assert auto_cleanup_include_squash is False


class TestShowSummary:
    """Tests for show_summary function."""

    def test_shows_summary_table(self) -> None:
        """Test that summary table is displayed."""
        with patch("setup_repo.cli.commands.init_display.console") as mock_console:
            show_summary(
                github_owner="test-owner",
                github_token="token",
                workspace_dir=Path("/workspace"),
                max_workers=10,
                use_https=True,
                ssl_no_verify=False,
                log_enabled=False,
                log_file=None,
                auto_prune=True,
                auto_stash=False,
                auto_cleanup=False,
                auto_cleanup_include_squash=False,
            )

        mock_console.print.assert_called_once()

    def test_shows_log_file_when_enabled(self) -> None:
        """Test that log file path is shown when logging is enabled."""
        with patch("setup_repo.cli.commands.init_display.console") as mock_console:
            show_summary(
                github_owner="test-owner",
                github_token=None,
                workspace_dir=Path("/workspace"),
                max_workers=5,
                use_https=False,
                ssl_no_verify=True,
                log_enabled=True,
                log_file=Path("/var/log/test.jsonl"),
                auto_prune=False,
                auto_stash=True,
                auto_cleanup=True,
                auto_cleanup_include_squash=True,
            )

        mock_console.print.assert_called_once()


class TestInit:
    """Tests for init function."""

    def test_init_saves_config(self, tmp_path: Path) -> None:
        """Test that init saves configuration."""
        config_path = tmp_path / "config.toml"

        with patch("setup_repo.cli.commands.init.AppSettings") as mock_settings_cls:
            mock_settings = MagicMock()
            mock_settings.github_owner = "test-owner"
            mock_settings.github_token = "test-token"
            mock_settings.workspace_dir = Path("/workspace")
            mock_settings.max_workers = 10
            mock_settings_cls.return_value = mock_settings

            with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
                # Confirm calls in order:
                # 1. Use detected owner? True
                # 2. Use detected token? True
                # 3. Use default workspace? True
                # 4. Use default workers? True
                # 5. Enable file logging? False
                # 6. Enable auto prune? True
                # 7. Enable auto stash? False
                # 8. Enable auto cleanup? False
                # 9. Save config? True
                mock_confirm.ask.side_effect = [True, True, True, True, False, True, False, False, True]
                with patch("setup_repo.cli.commands.init_validators.Confirm") as mock_git_confirm:
                    mock_git_confirm.ask.return_value = False  # SSL verify remains enabled
                    with patch("setup_repo.cli.commands.init_validators.Prompt") as mock_prompt:
                        mock_prompt.ask.return_value = "1"  # HTTPS

                        with (
                            patch("setup_repo.cli.commands.init.console"),
                            patch("setup_repo.cli.commands.init_validators.console"),
                            patch("setup_repo.cli.commands.init_wizard.console"),
                            patch("setup_repo.cli.commands.init.get_config_path", return_value=config_path),
                        ):
                            init()

        assert config_path.exists()
        content = config_path.read_text()
        assert "test-owner" in content

    def test_init_cancelled(self) -> None:
        """Test that init exits when cancelled."""
        with patch("setup_repo.cli.commands.init.AppSettings") as mock_settings_cls:
            mock_settings = MagicMock()
            mock_settings.github_owner = "owner"
            mock_settings.github_token = None
            mock_settings.workspace_dir = Path("/workspace")
            mock_settings.max_workers = 10
            mock_settings_cls.return_value = mock_settings

            with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
                # Confirm calls in order:
                # 1. Use detected owner? True
                # 2. Use default workspace? True
                # 3. Use default workers? True
                # 4. Enable file logging? False
                # 5. Enable auto prune? True
                # 6. Enable auto stash? False
                # 7. Enable auto cleanup? False
                # 8. Save config? False (cancel)
                mock_confirm.ask.side_effect = [True, True, True, False, True, False, False, False]
                with patch("setup_repo.cli.commands.init_wizard.Prompt") as mock_wizard_prompt:
                    mock_wizard_prompt.ask.return_value = ""  # Empty token
                    with patch("setup_repo.cli.commands.init_validators.Confirm") as mock_git_confirm:
                        mock_git_confirm.ask.return_value = False
                        with patch("setup_repo.cli.commands.init_validators.Prompt") as mock_prompt:
                            mock_prompt.ask.return_value = "1"  # HTTPS

                            with (
                                patch("setup_repo.cli.commands.init.console"),
                                patch("setup_repo.cli.commands.init_validators.console"),
                                patch("setup_repo.cli.commands.init_wizard.console"),
                                pytest.raises(typer.Exit) as exc_info,
                            ):
                                init()

        assert exc_info.value.exit_code == 0

    def test_init_save_error(self, tmp_path: Path) -> None:
        """Test that init handles save errors."""
        # Create a path that will fail to write (directory that doesn't exist and can't be created)
        with patch("setup_repo.cli.commands.init.AppSettings") as mock_settings_cls:
            mock_settings = MagicMock()
            mock_settings.github_owner = "owner"
            mock_settings.github_token = "token"
            mock_settings.workspace_dir = Path("/workspace")
            mock_settings.max_workers = 10
            mock_settings_cls.return_value = mock_settings

            with patch("setup_repo.cli.commands.init_wizard.Confirm") as mock_confirm:
                # Confirm calls in order:
                # 1. Use detected owner? True
                # 2. Use detected token? True
                # 3. Use default workspace? True
                # 4. Use default workers? True
                # 5. Enable file logging? False
                # 6. Enable auto prune? True
                # 7. Enable auto stash? False
                # 8. Enable auto cleanup? False
                # 9. Save config? True
                mock_confirm.ask.side_effect = [True, True, True, True, False, True, False, False, True]
                with patch("setup_repo.cli.commands.init_validators.Confirm") as mock_git_confirm:
                    mock_git_confirm.ask.return_value = False
                    with patch("setup_repo.cli.commands.init_validators.Prompt") as mock_prompt:
                        mock_prompt.ask.return_value = "1"  # HTTPS

                        with (
                            patch("setup_repo.cli.commands.init.console"),
                            patch("setup_repo.cli.commands.init_validators.console"),
                            patch("setup_repo.cli.commands.init_wizard.console"),
                            patch("setup_repo.cli.commands.init.save_config") as mock_save,
                            pytest.raises(typer.Exit) as exc_info,
                        ):
                            mock_save.side_effect = OSError("Write error")
                            init()

        assert exc_info.value.exit_code == 1

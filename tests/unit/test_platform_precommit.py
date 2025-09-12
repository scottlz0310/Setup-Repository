"""
precommit環境でのプラットフォーム検出テスト

このモジュールは、precommit環境でのプラットフォーム検出が
適切に動作することをテストします。
"""

import os
from unittest.mock import mock_open, patch

import pytest

from src.setup_repo.platform_detector import PlatformDetector, detect_platform


@pytest.mark.unit
class TestPrecommitPlatformDetection:
    """precommit環境でのプラットフォーム検出テスト"""

    def test_wsl_detection_in_precommit_environment(self):
        """precommit環境でのWSL検出テスト"""
        import platform as platform_module

        current_platform = platform_module.system().lower()

        # CI環境でWindows以外でのみテストを実行
        if current_platform == "windows":
            pytest.skip("Windows環境でWSL検出テストをスキップ")

        with (
            patch("src.setup_repo.platform_detector.platform.system") as mock_system,
            patch("src.setup_repo.platform_detector.platform.release") as mock_release,
            patch("src.setup_repo.platform_detector.os.name", "posix"),
            patch("src.setup_repo.platform_detector.os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data="Linux version 5.4.0-microsoft-standard-WSL2")),
            patch.dict(
                os.environ,
                {
                    "PRE_COMMIT": "1",  # precommit環境
                    "CI": "false",
                    "GITHUB_ACTIONS": "false",
                },
            ),
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-microsoft-standard-WSL2"

            platform_info = detect_platform()

            # precommit環境ではWSLとして検出される
            assert platform_info.name == "wsl"
            assert platform_info.display_name == "WSL (Windows Subsystem for Linux)"
            assert platform_info.shell == "bash"
            assert platform_info.python_cmd == "python3"

    def test_linux_detection_in_precommit_environment(self):
        """precommit環境での通常のLinux検出テスト"""
        import platform as platform_module

        current_platform = platform_module.system().lower()

        # CI環境でWindows以外でのみテストを実行
        if current_platform == "windows":
            pytest.skip("Windows環境でLinux検出テストをスキップ")

        with (
            patch("src.setup_repo.platform_detector.platform.system") as mock_system,
            patch("src.setup_repo.platform_detector.platform.release") as mock_release,
            patch("src.setup_repo.platform_detector.os.name", "posix"),
            patch("src.setup_repo.platform_detector.os.path.exists", return_value=False),
            patch.dict(
                os.environ,
                {
                    "PRE_COMMIT": "1",  # precommit環境
                    "CI": "false",
                    "GITHUB_ACTIONS": "false",
                },
            ),
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-generic"  # WSLではない

            platform_info = detect_platform()

            # precommit環境でも通常のLinuxはlinuxとして検出される
            assert platform_info.name == "linux"
            assert platform_info.display_name == "Linux"
            assert platform_info.shell == "bash"
            assert platform_info.python_cmd == "python3"

    def test_platform_detector_precommit_environment_detection(self):
        """PlatformDetectorクラスでのprecommit環境検出テスト"""
        detector = PlatformDetector()

        with patch.dict(os.environ, {"PRE_COMMIT": "1"}):
            assert detector.is_precommit_environment() is True

        with patch.dict(os.environ, {"PRE_COMMIT": "0"}):
            assert detector.is_precommit_environment() is False

        with patch.dict(os.environ, {}, clear=True):
            assert detector.is_precommit_environment() is False

    def test_ci_vs_precommit_wsl_detection(self):
        """CI環境とprecommit環境でのWSL検出の違いをテスト"""
        import platform as platform_module

        current_platform = platform_module.system().lower()

        # CI環境でWindows以外でのみテストを実行
        if current_platform == "windows":
            pytest.skip("Windows環境でWSL検出テストをスキップ")

        # CI環境でのWSL検出
        with (
            patch("src.setup_repo.platform_detector.platform.system") as mock_system,
            patch("src.setup_repo.platform_detector.platform.release") as mock_release,
            patch("src.setup_repo.platform_detector.os.name", "posix"),
            patch("src.setup_repo.platform_detector.os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data="Linux version 5.4.0-microsoft-standard-WSL2")),
            patch.dict(
                os.environ,
                {
                    "CI": "true",
                    "GITHUB_ACTIONS": "true",
                    "RUNNER_OS": "Linux",
                },
            ),
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-microsoft-standard-WSL2"

            ci_platform_info = detect_platform()

        # precommit環境でのWSL検出
        with (
            patch("src.setup_repo.platform_detector.platform.system") as mock_system,
            patch("src.setup_repo.platform_detector.platform.release") as mock_release,
            patch("src.setup_repo.platform_detector.os.name", "posix"),
            patch("src.setup_repo.platform_detector.os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data="Linux version 5.4.0-microsoft-standard-WSL2")),
            patch.dict(
                os.environ,
                {
                    "PRE_COMMIT": "1",
                    "CI": "false",
                    "GITHUB_ACTIONS": "false",
                },
            ),
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-microsoft-standard-WSL2"

            precommit_platform_info = detect_platform()

        # CI環境ではlinux、precommit環境ではwslとして検出される
        assert ci_platform_info.name == "linux"
        assert precommit_platform_info.name == "wsl"

        # 表示名も適切に設定される
        assert "WSL in CI" in ci_platform_info.display_name
        assert precommit_platform_info.display_name == "WSL (Windows Subsystem for Linux)"

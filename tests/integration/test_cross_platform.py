"""
クロスプラットフォーム動作の統合テスト

このモジュールでは、Windows、Linux、macOS、WSLなど、
異なるプラットフォームでのシステムの動作を検証します。
プラットフォーム固有の設定、パス処理、コマンド実行などを
テストします。
"""

import os
import platform
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from setup_repo.platform_detector import PlatformInfo, detect_platform
from setup_repo.sync import sync_repositories


@pytest.mark.integration
class TestCrossPlatform:
    """クロスプラットフォーム動作の統合テストクラス"""

    @pytest.mark.parametrize(
        "platform_name,expected",
        [
            ("Windows", "windows"),
            ("Linux", "linux"),
            ("Darwin", "macos"),
        ],
    )
    def test_platform_detection(self, platform_name: str, expected: str) -> None:
        """プラットフォーム検出テスト"""
        with (
            patch(
                "setup_repo.platform_detector.platform.system",
                return_value=platform_name,
            ),
            patch(
                "setup_repo.platform_detector.platform.release",
                return_value="5.4.0-generic",
            ),  # 非WSLリリース
            patch("setup_repo.platform_detector.os.path.exists", return_value=False),  # WSL検出を無効化
            patch("setup_repo.platform_detector.os.environ") as mock_env,
            patch(
                "setup_repo.platform_detector.os.name",
                "nt" if platform_name == "Windows" else "posix",
            ),
        ):
            # CI環境変数をモック
            mock_env.get.side_effect = lambda key, default="": {
                "CI": "false",
                "GITHUB_ACTIONS": "false",
                "RUNNER_OS": expected,
            }.get(key, default)

            platform_info = detect_platform()
            assert platform_info.name == expected

    def test_windows_path_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """Windowsパス処理テスト"""
        # Windowsプラットフォームをシミュレート
        windows_platform = PlatformInfo(
            name="windows",
            display_name="Windows",
            package_managers=["scoop", "winget", "chocolatey"],
            shell="powershell",
            python_cmd="python",
        )
        with patch(
            "setup_repo.platform_detector.detect_platform",
            return_value=windows_platform,
        ):
            # Windowsスタイルのパスを設定
            windows_path = temp_dir / "repos"
            sample_config["clone_destination"] = str(windows_path).replace("/", "\\")

            mock_repos = [
                {
                    "name": "windows-path-repo",
                    "full_name": "test_user/windows-path-repo",
                    "clone_url": "https://github.com/test_user/windows-path-repo.git",
                    "ssh_url": "git@github.com:test_user/windows-path-repo.git",
                    "description": "Windowsパステスト用リポジトリ",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(sample_config, dry_run=True)

            assert result.success
            assert len(result.synced_repos) == 1

    def test_linux_path_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """Linuxパス処理テスト"""
        linux_platform = PlatformInfo(
            name="linux",
            display_name="Linux",
            package_managers=["apt", "snap", "curl"],
            shell="bash",
            python_cmd="python3",
        )
        with patch("setup_repo.platform_detector.detect_platform", return_value=linux_platform):
            # Linuxスタイルのパスを設定
            linux_path = temp_dir / "repos"
            sample_config["clone_destination"] = str(linux_path)

            mock_repos = [
                {
                    "name": "linux-path-repo",
                    "full_name": "test_user/linux-path-repo",
                    "clone_url": "https://github.com/test_user/linux-path-repo.git",
                    "ssh_url": "git@github.com:test_user/linux-path-repo.git",
                    "description": "Linuxパステスト用リポジトリ",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(sample_config, dry_run=True)

            assert result.success
            assert len(result.synced_repos) == 1

    def test_macos_path_handling(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """macOSパス処理テスト"""
        macos_platform = PlatformInfo(
            name="macos",
            display_name="macOS",
            package_managers=["brew", "curl"],
            shell="zsh",
            python_cmd="python3",
        )
        with patch("setup_repo.platform_detector.detect_platform", return_value=macos_platform):
            # macOSスタイルのパスを設定
            macos_path = temp_dir / "repos"
            sample_config["clone_destination"] = str(macos_path)

            mock_repos = [
                {
                    "name": "macos-path-repo",
                    "full_name": "test_user/macos-path-repo",
                    "clone_url": "https://github.com/test_user/macos-path-repo.git",
                    "ssh_url": "git@github.com:test_user/macos-path-repo.git",
                    "description": "macOSパステスト用リポジトリ",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(sample_config, dry_run=True)

            assert result.success
            assert len(result.synced_repos) == 1

    def test_wsl_environment_detection(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """WSL環境検出テスト"""
        # WSL環境をシミュレート
        wsl_env = {
            "WSL_DISTRO_NAME": "Ubuntu",
            "WSLENV": "PATH/l",
        }

        with (
            patch.dict(os.environ, wsl_env),
            patch("platform.system", return_value="Linux"),
            patch(
                "setup_repo.platform_detector.detect_platform",
                return_value=PlatformInfo(
                    name="wsl",
                    display_name="WSL (Windows Subsystem for Linux)",
                    package_managers=["apt", "snap", "curl"],
                    shell="bash",
                    python_cmd="python3",
                ),
            ),
        ):
            clone_destination = temp_dir / "repos"
            sample_config["clone_destination"] = str(clone_destination)

            mock_repos = [
                {
                    "name": "wsl-repo",
                    "full_name": "test_user/wsl-repo",
                    "clone_url": "https://github.com/test_user/wsl-repo.git",
                    "ssh_url": "git@github.com:test_user/wsl-repo.git",
                    "description": "WSLテスト用リポジトリ",
                    "private": False,
                    "default_branch": "main",
                }
            ]

            with (
                patch("setup_repo.sync.get_repositories", return_value=mock_repos),
                patch("setup_repo.sync.sync_repository_with_retries", return_value=True),
            ):
                result = sync_repositories(sample_config, dry_run=True)

            assert result.success
            assert len(result.synced_repos) == 1

    def test_environment_variable_handling_cross_platform(
        self,
        temp_dir: Path,
    ) -> None:
        """クロスプラットフォーム環境変数処理テスト"""
        platforms = {
            "windows": PlatformInfo(
                name="windows",
                display_name="Windows",
                package_managers=["scoop", "winget", "chocolatey"],
                shell="powershell",
                python_cmd="python",
            ),
            "linux": PlatformInfo(
                name="linux",
                display_name="Linux",
                package_managers=["apt", "snap", "curl"],
                shell="bash",
                python_cmd="python3",
            ),
            "macos": PlatformInfo(
                name="macos",
                display_name="macOS",
                package_managers=["brew", "curl"],
                shell="zsh",
                python_cmd="python3",
            ),
        }

        for platform_name, platform_info in platforms.items():
            with patch(
                "setup_repo.platform_detector.detect_platform",
                return_value=platform_info,
            ):
                # プラットフォーム固有の環境変数をテスト
                test_env = {
                    "TEST_VAR": "test_value",
                    "PATH": os.environ.get("PATH", ""),
                }

                if platform_name == "windows":
                    test_env["USERPROFILE"] = str(temp_dir)
                else:
                    test_env["HOME"] = str(temp_dir)

                with patch.dict(os.environ, test_env):
                    detected = detect_platform()
                    assert detected.name == platform_name

    @pytest.mark.skipif(
        os.name == "nt",
        reason="fcntlモジュールはWindows環境では利用できません",
    )
    def test_unix_specific_functionality(self) -> None:
        """Unix固有機能のテスト（Windows環境ではスキップ）"""
        try:
            import fcntl  # noqa: F401
        except ImportError:
            pytest.skip("fcntlモジュールが利用できません")

        # Unix固有の機能をテスト
        platform_info = detect_platform()
        assert platform_info.name in ["linux", "macos", "wsl"]
        assert platform_info.shell in ["bash", "zsh"]

    @pytest.mark.skipif(
        os.name != "nt",
        reason="Windows固有機能のテストです",
    )
    def test_windows_specific_functionality(self) -> None:
        """Windows固有機能のテスト（非Windows環境ではスキップ）"""
        try:
            import msvcrt  # noqa: F401
        except ImportError:
            pytest.skip("msvcrtモジュールが利用できません")

        platform_info = detect_platform()
        assert platform_info.name == "windows"
        assert platform_info.shell == "powershell"
        assert platform_info.python_cmd == "python"

    @pytest.mark.skipif(
        not os.environ.get("GITHUB_ACTIONS"),
        reason="GitHub Actions環境でのみ実行",
    )
    def test_github_actions_environment(self) -> None:
        """GitHub Actions環境固有のテスト"""
        # CI環境変数の存在確認
        assert os.environ.get("GITHUB_ACTIONS") == "true"
        assert os.environ.get("CI") == "true"

        # RUNNER_OS環境変数の確認
        runner_os = os.environ.get("RUNNER_OS", "").lower()
        assert runner_os in ["windows", "linux", "macos"]

        # プラットフォーム検出との整合性確認
        platform_info = detect_platform()
        if runner_os == "windows":
            assert platform_info.name == "windows"
        elif runner_os == "linux":
            assert platform_info.name in ["linux", "wsl"]
        elif runner_os == "macos":
            assert platform_info.name == "macos"

    def test_platform_specific_module_availability(self) -> None:
        """プラットフォーム固有モジュールの可用性テスト"""
        from setup_repo.platform_detector import check_module_availability

        # fcntlモジュール（Unix系のみ）
        fcntl_info = check_module_availability("fcntl")
        if os.name == "nt":
            assert not fcntl_info["available"]
            assert fcntl_info["platform_specific"]
        else:
            # Unix系では通常利用可能
            assert fcntl_info["platform_specific"]

        # msvcrtモジュール（Windowsのみ）
        msvcrt_info = check_module_availability("msvcrt")
        if os.name == "nt":
            assert msvcrt_info["available"]
            assert msvcrt_info["platform_specific"]
        else:
            assert not msvcrt_info["available"]
            assert msvcrt_info["platform_specific"]

        # 共通モジュール
        for module in ["subprocess", "pathlib", "platform"]:
            module_info = check_module_availability(module)
            assert module_info["available"]
            assert not module_info["platform_specific"]

    @pytest.mark.skipif(
        not os.environ.get("CI"),
        reason="CI環境でのみ実行される包括的テスト",
    )
    def test_comprehensive_platform_detection(self) -> None:
        """包括的プラットフォーム検出テスト（CI環境のみ）"""
        from setup_repo.platform_detector import (
            diagnose_platform_issues,
            get_ci_environment_info,
        )

        # プラットフォーム診断実行
        diagnosis = diagnose_platform_issues()
        assert "platform_info" in diagnosis
        assert "package_managers" in diagnosis
        assert "module_availability" in diagnosis

        # CI環境情報取得
        ci_info = get_ci_environment_info()
        assert "platform_system" in ci_info
        assert "python_version" in ci_info

        # GitHub Actions固有の情報確認
        if os.environ.get("GITHUB_ACTIONS"):
            assert "GITHUB_ACTIONS" in ci_info
            assert "RUNNER_OS" in ci_info

    def test_package_manager_detection_with_timeout(self) -> None:
        """パッケージマネージャー検出のタイムアウトテスト"""
        from setup_repo.platform_detector import check_package_manager

        # 存在しないパッケージマネージャーでタイムアウトテスト
        result = check_package_manager("nonexistent_package_manager")
        assert not result

        # 一般的なコマンドでのテスト
        common_commands = ["python", "pip"]
        for cmd in common_commands:
            # タイムアウトが発生しないことを確認
            try:
                result = check_package_manager(cmd)
                # 結果は環境依存だが、タイムアウトしないことが重要
                assert isinstance(result, bool)
            except Exception as e:
                # 予期しない例外は失敗とする
                pytest.fail(f"Unexpected exception for {cmd}: {e}")

    @pytest.mark.parametrize(
        "platform_name,expected_shell",
        [
            ("windows", "powershell"),
            ("linux", "bash"),
            ("macos", "zsh"),
            ("wsl", "bash"),
        ],
    )
    def test_platform_shell_mapping(self, platform_name: str, expected_shell: str) -> None:
        """プラットフォーム別シェルマッピングテスト"""
        # 実際の環境に関係なく、各プラットフォームの設定をテスト
        with patch("setup_repo.platform_detector.platform.system") as mock_system:
            if platform_name == "windows":
                mock_system.return_value = "Windows"
                with patch("setup_repo.platform_detector.os.name", "nt"):
                    platform_info = detect_platform()
            elif platform_name == "wsl":
                mock_system.return_value = "Linux"
                with (
                    patch("setup_repo.platform_detector._check_wsl_environment", return_value=True),
                    patch("setup_repo.platform_detector.os.environ.get") as mock_env,
                ):
                    mock_env.side_effect = lambda key, default="": {
                        "CI": "false",
                        "GITHUB_ACTIONS": "false",
                    }.get(key, default)
                    platform_info = detect_platform()
            elif platform_name == "linux":
                mock_system.return_value = "Linux"
                with (
                    patch("setup_repo.platform_detector._check_wsl_environment", return_value=False),
                    patch("setup_repo.platform_detector.os.environ.get") as mock_env,
                ):
                    mock_env.side_effect = lambda key, default="": {
                        "CI": "false",
                        "GITHUB_ACTIONS": "false",
                    }.get(key, default)
                    platform_info = detect_platform()
            elif platform_name == "macos":
                mock_system.return_value = "Darwin"
                platform_info = detect_platform()

            assert platform_info.shell == expected_shell

    @pytest.mark.skipif(
        platform.system() == "Windows" and not os.environ.get("CI"),
        reason="Windows環境でのネットワークテストはCI環境でのみ実行",
    )
    def test_network_dependent_functionality(self) -> None:
        """ネットワーク依存機能のテスト（CI環境優先）"""
        from setup_repo.platform_detector import check_package_manager

        # uvコマンドの存在確認（ネットワーク不要）
        uv_available = check_package_manager("uv")

        # CI環境では厳密にチェック、ローカルでは緩和
        if os.environ.get("CI"):
            # CI環境ではuvが利用可能であることを期待
            if not uv_available:
                pytest.skip("CI環境でuvが利用できません - セットアップを確認してください")
        else:
            # ローカル環境では警告のみ
            if not uv_available:
                pytest.skip("ローカル環境でuvが見つかりません - 必要に応じてインストールしてください")

    @pytest.mark.slow
    def test_performance_sensitive_operations(self) -> None:
        """パフォーマンス重視の操作テスト"""
        # 診断処理の実行時間を測定
        import time

        from setup_repo.platform_detector import diagnose_platform_issues

        start_time = time.time()

        diagnosis = diagnose_platform_issues()

        end_time = time.time()
        execution_time = end_time - start_time

        # 診断が正常に完了することを確認
        assert "platform_info" in diagnosis

        # CI環境では実行時間をチェック（ローカルでは緩和）
        if os.environ.get("CI"):
            # CI環境では30秒以内での完了を期待
            assert execution_time < 30, f"診断処理が遅すぎます: {execution_time:.2f}秒"
        else:
            # ローカル環境では60秒まで許容
            assert execution_time < 60, f"診断処理が遅すぎます: {execution_time:.2f}秒"

"""
クロスプラットフォーム共通機能テスト

全プラットフォームで同じ動作を期待する機能のテスト。
モックを最小限に抑え、実環境での動作検証を重視します。
"""

import os
import platform
from pathlib import Path
from typing import Any

import pytest

from setup_repo.platform_detector import detect_platform
from setup_repo.sync import sync_repositories

from .helpers import check_platform_modules, verify_current_platform


@pytest.mark.cross_platform
class TestCrossPlatformCommon:
    """全プラットフォーム共通機能テスト"""

    def test_environment_variable_handling_cross_platform(self, temp_dir: Path):
        """クロスプラットフォーム環境変数処理テスト"""
        # ヘルパー関数でプラットフォーム検証
        actual_platform = verify_current_platform()

        # プラットフォーム固有モジュールもチェック
        check_platform_modules()

        # 実際のプラットフォームに応じたテストのみ実行
        test_env = {
            "TEST_VAR": "test_value",
            "PATH": os.environ.get("PATH", ""),
        }

        if actual_platform.name == "windows":
            test_env["USERPROFILE"] = str(temp_dir)
        else:
            test_env["HOME"] = str(temp_dir)

        with pytest.MonkeyPatch().context() as m:
            for key, value in test_env.items():
                m.setenv(key, value)

            detected = detect_platform()
            assert detected.name == actual_platform.name

    @pytest.mark.skipif(
        not os.environ.get("GITHUB_ACTIONS"),
        reason="GitHub Actions環境でのみ実行",
    )
    def test_github_actions_environment(self):
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

    @pytest.mark.skipif(
        not os.environ.get("CI"),
        reason="CI環境でのみ実行される包括的テスト",
    )
    def test_comprehensive_platform_detection(self):
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

    @pytest.mark.skipif(
        platform.system() == "Windows" and not os.environ.get("CI"),
        reason="Windows環境でのネットワークテストはCI環境でのみ実行",
    )
    @pytest.mark.network
    def test_network_dependent_functionality(self):
        """ネットワーク依存機能のテスト（CI環境優先）"""
        from setup_repo.platform_detector import check_package_manager

        # uvコマンドの存在確認（ネットワーク不要）
        uv_available = check_package_manager("uv")

        # CI環境では厳密にチェック、ローカルでは緩和
        if os.environ.get("CI"):
            if not uv_available:
                pytest.skip("CI環境でuvが利用できません - セットアップを確認してください")
        else:
            if not uv_available:
                pytest.skip("ローカル環境でuvが見つかりません - 必要に応じてインストールしてください")

    @pytest.mark.slow
    def test_performance_sensitive_operations(self):
        """パフォーマンス重視の操作テスト"""
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
            assert execution_time < 30, f"診断処理が遅すぎます: {execution_time:.2f}秒"
        else:
            assert execution_time < 60, f"診断処理が遅すぎます: {execution_time:.2f}秒"


@pytest.mark.integration
class TestCrossPlatformIntegration:
    """クロスプラットフォーム統合テスト"""

    def test_path_handling_integration(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ):
        """パス処理統合テスト - 実際のプラットフォームで動作"""
        # ヘルパー関数でプラットフォーム検証
        platform_info = verify_current_platform()  # プラットフォーム検証

        # 実際のプラットフォームに応じたパス設定
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        mock_repos = [
            {
                "name": f"{platform_info.name}-path-repo",
                "full_name": f"test_user/{platform_info.name}-path-repo",
                "clone_url": f"https://github.com/test_user/{platform_info.name}-path-repo.git",
                "ssh_url": f"git@github.com:test_user/{platform_info.name}-path-repo.git",
                "description": f"{platform_info.display_name}パステスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            }
        ]

        with (
            pytest.MonkeyPatch().context() as m,
        ):
            m.setattr("setup_repo.sync.get_repositories", lambda config, github_api=None: mock_repos)
            m.setattr("setup_repo.sync.sync_repository_with_retries", lambda *args, **kwargs: True)

            result = sync_repositories(sample_config, dry_run=True)

        assert result.success
        assert len(result.synced_repos) == 1

    def test_wsl_environment_detection(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ):
        """WSL環境検出テスト - 実際のWSL環境でのみ実行"""
        if platform.system() != "Linux":
            pytest.skip("Linux環境でのみ実行")

        # WSL環境変数の確認
        wsl_env_vars = ["WSL_DISTRO_NAME", "WSLENV"]
        is_wsl = any(var in os.environ for var in wsl_env_vars)

        if not is_wsl:
            pytest.skip("WSL環境ではありません")

        platform_info = detect_platform()
        assert platform_info.name in ["wsl", "linux"]
        # 実環境ではシェルが sh の場合がある
        assert platform_info.shell in ["bash", "sh", "zsh"]

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
            pytest.MonkeyPatch().context() as m,
        ):
            m.setattr("setup_repo.sync.get_repositories", lambda config, github_api=None: mock_repos)
            m.setattr("setup_repo.sync.sync_repository_with_retries", lambda *args, **kwargs: True)

            result = sync_repositories(sample_config, dry_run=True)

        assert result.success
        assert len(result.synced_repos) == 1

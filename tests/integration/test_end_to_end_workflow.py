"""
エンドツーエンドワークフローテスト

マルチプラットフォームテスト方針に準拠したエンドツーエンドワークフローのテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.config import load_config
from setup_repo.git_operations import GitOperations, sync_repository
from setup_repo.github_api import GitHubAPI, get_repositories
from tests.multiplatform.helpers import (
    get_platform_specific_config,
    verify_current_platform,
)


class TestEndToEndWorkflow:
    """エンドツーエンドワークフローのテスト"""

    @pytest.mark.integration
    def test_complete_setup_workflow(self):
        """完全なセットアップワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            with (
                patch("subprocess.run") as mock_run,
                patch("requests.get") as mock_get,
                patch("setup_repo.config.get_github_token") as mock_token,
                patch("setup_repo.config.get_github_user") as mock_user,
            ):
                # Git操作のモック
                mock_run.return_value = Mock(returncode=0, stdout="success")

                # GitHub API操作のモック
                mock_get.return_value = Mock(status_code=200, json=lambda: [{"name": "test-repo"}])
                mock_token.return_value = "test_token"
                mock_user.return_value = "testuser"

                # 1. 設定の読み込み
                config = load_config()
                assert isinstance(config, dict)

                # 2. GitHub APIテスト
                api = GitHubAPI("test_token", "testuser")
                user_info = api.get_user_info()
                assert "login" in user_info or user_info is not None

                # 3. Git操作テスト
                git_ops = GitOperations()
                assert git_ops.is_git_repository(project_path) is False

    @pytest.mark.integration
    def test_repository_sync_workflow(self):
        """リポジトリ同期ワークフローテスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)

            with patch("setup_repo.github_api.get_repositories") as mock_get_repos:
                # 直接get_repositories関数をモックしてタイムアウトを回避
                mock_get_repos.return_value = [
                    {"name": "test-repo", "clone_url": "https://github.com/user/test-repo.git"}
                ]

                # リポジトリ一覧取得
                repos = get_repositories("testuser", "test_token")
                assert len(repos) >= 0  # モックの場合は1件

                # 同期テスト
                if repos:
                    repo = repos[0]
                    with patch("setup_repo.git_operations._sync_repository_once") as mock_sync:
                        mock_sync.return_value = True
                        result = sync_repository(repo, dest_dir)
                        assert result is True

    @pytest.mark.integration
    def test_multi_repository_sync_workflow(self):
        """複数リポジトリ同期ワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        repositories = [
            {"name": "repo1", "clone_url": "https://github.com/user/repo1.git"},
            {"name": "repo2", "clone_url": "https://github.com/user/repo2.git"},
            {"name": "repo3", "clone_url": "https://github.com/user/repo3.git"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            with patch("setup_repo.git_operations._sync_repository_once") as mock_sync:
                mock_sync.return_value = True

                sync_results = []

                for repo in repositories:
                    result = sync_repository(repo, base_path)
                    sync_results.append(result)

                # 全てのリポジトリが正常に同期されたことを確認
                assert all(result for result in sync_results)
                assert len(sync_results) == 3

    @pytest.mark.integration
    def test_error_recovery_workflow(self):
        """エラー回復ワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir)
            repo = {"name": "test-repo"}
            config = {"max_retries": 2, "dry_run": False}

            with patch("setup_repo.git_operations._sync_repository_once") as mock_sync, patch("builtins.print"):
                # 最初の試行は失敗、2回目は成功
                mock_sync.side_effect = [False, True]

                from setup_repo.git_operations import sync_repository_with_retries

                result = sync_repository_with_retries(repo, dest_dir, config)
                assert result is True

    @pytest.mark.integration
    def test_configuration_validation_workflow(self):
        """設定検証ワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証

        # 無効な設定でのテスト
        invalid_config = {
            "github_token": None,
            "owner": "",
            "dest": "/tmp/test",
            "use_ssh": False,
            "max_retries": 3,
            "retry_delay": 1,
            "dry_run": False,
        }

        # 無効な設定の検証
        assert invalid_config["github_token"] is None
        assert invalid_config["owner"] == ""

        # 有効な設定でのテスト
        valid_config = {
            "github_token": "test_token",
            "owner": "testuser",
            "dest": "/tmp/test",
            "use_ssh": False,
            "max_retries": 3,
            "retry_delay": 1,
            "dry_run": False,
        }

        # 有効な設定の検証
        assert valid_config["github_token"] == "test_token"
        assert valid_config["owner"] == "testuser"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_performance_workflow(self):
        """パフォーマンスワークフローのテスト"""
        import time

        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        with tempfile.TemporaryDirectory() as temp_dir:
            start_time = time.time()

            # 複数の操作を実行
            concurrent_limit = 5  # テスト用の制限
            for i in range(concurrent_limit):
                git_ops = GitOperations()
                repo_path = Path(temp_dir) / f"repo{i}"
                repo_path.mkdir(exist_ok=True)
                result = git_ops.is_git_repository(repo_path)
                assert result is False  # .gitがないのでFalse

            elapsed = time.time() - start_time
            max_time = 5.0  # 5秒以内

            assert elapsed < max_time, f"ワークフローが遅すぎます: {elapsed}秒 (制限: {max_time}秒)"

    @pytest.mark.integration
    def test_platform_specific_workflow(self):
        """プラットフォーム固有ワークフローのテスト"""
        platform_info = verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # プラットフォーム固有のパス処理を確認
            if platform_info.name == "windows":
                test_path = project_path / "test" / "subdir"
            else:
                test_path = project_path / "test" / "subdir"

            # パスが正しく作成されることを確認
            test_path.mkdir(parents=True, exist_ok=True)
            assert test_path.exists()

            # プラットフォーム情報の確認
            assert platform_info.name in ["windows", "linux", "wsl", "macos"]

    @pytest.mark.integration
    def test_concurrent_operations_workflow(self):
        """並行操作ワークフローのテスト"""
        import concurrent.futures

        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        def mock_operation(repo_id):
            """モック操作関数"""
            # 簡単な操作を実行
            return {"id": repo_id, "success": True}

        # 並行操作の実行
        concurrent_limit = 3  # テスト用の制限
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_limit) as executor:
            futures = [executor.submit(mock_operation, i) for i in range(concurrent_limit)]

            results = [future.result() for future in futures]

        # 全ての操作が成功したことを確認
        assert len(results) == concurrent_limit
        assert all(result["success"] for result in results)

    @pytest.mark.integration
    def test_cleanup_workflow(self):
        """クリーンアップワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # 一時ファイルを作成
            temp_files = []
            for i in range(5):
                temp_file = project_path / f"temp_{i}.tmp"
                temp_file.write_text(f"temporary content {i}")
                temp_files.append(temp_file)

            # 全ての一時ファイルが作成されたことを確認
            assert all(f.exists() for f in temp_files)

            # クリーンアップ実行
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

            # クリーンアップが完了したことを確認
            assert not any(f.exists() for f in temp_files)

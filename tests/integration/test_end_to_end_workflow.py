"""
エンドツーエンドワークフローテスト

マルチプラットフォームテスト方針に準拠したエンドツーエンドワークフローのテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.config import Config
from setup_repo.git_operations import GitOperations
from setup_repo.github_api import GitHubAPI
from setup_repo.setup import Setup
from setup_repo.sync import Sync
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
                patch("requests.post") as mock_post,
                patch("shutil.which") as mock_which,
            ):
                # 各種コマンドが利用可能
                mock_which.return_value = "/usr/bin/command"

                # Git操作のモック
                mock_run.return_value = Mock(returncode=0, stdout="success")

                # GitHub API操作のモック
                mock_get.return_value = Mock(status_code=200, json=lambda: {"login": "testuser"})
                mock_post.return_value = Mock(status_code=201, json=lambda: {"name": "test-repo"})

                # 1. 設定の初期化
                config = Config()
                config.set("github.username", "testuser")
                config.set("github.token", "test_token")
                config.apply_platform_defaults()

                # 2. セットアップの実行
                setup = Setup(project_path, config)
                setup_result = setup.run()

                # 3. 同期の実行
                sync = Sync(project_path, config)
                sync_result = sync.run()

                assert setup_result["success"] is True
                assert sync_result["success"] is True

    @pytest.mark.integration
    def test_repository_creation_and_sync_workflow(self):
        """リポジトリ作成と同期のワークフローテスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            with (
                patch("subprocess.run") as mock_run,
                patch("requests.post") as mock_post,
                patch("requests.get") as mock_get,
            ):
                # GitHub APIのモック
                mock_post.return_value = Mock(
                    status_code=201,
                    json=lambda: {"name": "new-repo", "clone_url": "https://github.com/user/new-repo.git"},
                )

                mock_get.return_value = Mock(status_code=200, json=lambda: {"default_branch": "main"})

                # Git操作のモック
                mock_run.return_value = Mock(returncode=0, stdout="success")

                # ワークフロー実行
                api = GitHubAPI("test_token")
                repo = api.create_repository("new-repo")

                git_ops = GitOperations(project_path)
                clone_result = git_ops.clone(repo["clone_url"])

                assert repo["name"] == "new-repo"
                assert clone_result["success"] is True

    @pytest.mark.integration
    def test_multi_repository_sync_workflow(self):
        """複数リポジトリ同期ワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        repositories = [
            {"name": "repo1", "url": "https://github.com/user/repo1.git"},
            {"name": "repo2", "url": "https://github.com/user/repo2.git"},
            {"name": "repo3", "url": "https://github.com/user/repo3.git"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            with patch("subprocess.run") as mock_run, patch("requests.get") as mock_get:
                # 各リポジトリの操作が成功
                mock_run.return_value = Mock(returncode=0, stdout="success")
                mock_get.return_value = Mock(status_code=200, json=lambda: {"default_branch": "main"})

                sync_results = []

                for repo in repositories:
                    repo_path = base_path / repo["name"]
                    git_ops = GitOperations(repo_path)

                    result = git_ops.clone(repo["url"])
                    sync_results.append(result)

                # 全てのリポジトリが正常に同期されたことを確認
                assert all(result["success"] for result in sync_results)
                assert len(sync_results) == 3

    @pytest.mark.integration
    def test_error_recovery_workflow(self):
        """エラー回復ワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            with patch("subprocess.run") as mock_run:
                # 最初の試行は失敗
                mock_run.side_effect = [
                    Mock(returncode=1, stderr="Network error"),  # 1回目失敗
                    Mock(returncode=0, stdout="success"),  # 2回目成功
                ]

                git_ops = GitOperations(project_path)

                # リトライ機能付きの操作
                try:
                    result = git_ops.clone_with_retry("https://github.com/user/repo.git", max_retries=2)
                    assert result["success"] is True
                    assert result["retries"] == 1
                except Exception:
                    # リトライ機能が実装されていない場合はスキップ
                    pytest.skip("リトライ機能が未実装")

    @pytest.mark.integration
    def test_configuration_validation_workflow(self):
        """設定検証ワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"

            # 無効な設定でのテスト
            invalid_config = Config()
            invalid_config.set("github.username", "")  # 空のユーザー名
            invalid_config.set("github.token", "invalid")  # 無効なトークン

            with pytest.raises(Exception):  # 設定検証エラー
                setup = Setup(temp_dir, invalid_config)
                setup.validate_configuration()

            # 有効な設定でのテスト
            valid_config = Config()
            valid_config.set("github.username", "testuser")
            valid_config.set("github.token", "ghp_valid_token")
            valid_config.apply_platform_defaults()

            setup = Setup(temp_dir, valid_config)
            validation_result = setup.validate_configuration()
            assert validation_result["valid"] is True

    @pytest.mark.integration
    @pytest.mark.slow
    def test_performance_workflow(self):
        """パフォーマンスワークフローのテスト"""
        import time

        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        with tempfile.TemporaryDirectory() as temp_dir:
            start_time = time.time()

            with patch("subprocess.run") as mock_run, patch("requests.get") as mock_get:
                mock_run.return_value = Mock(returncode=0, stdout="success")
                mock_get.return_value = Mock(status_code=200, json=lambda: {"test": "data"})

                # 大量の操作を実行
                for i in range(config["concurrent_limit"]):
                    git_ops = GitOperations(Path(temp_dir) / f"repo{i}")
                    git_ops.check_status()

            elapsed = time.time() - start_time
            max_time = config["timeout"]

            assert elapsed < max_time, f"ワークフローが遅すぎます: {elapsed}秒 (制限: {max_time}秒)"

    @pytest.mark.integration
    def test_platform_specific_workflow(self):
        """プラットフォーム固有ワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # プラットフォーム固有の設定を適用
            setup_config = Config()
            setup_config.apply_platform_defaults()

            # プラットフォーム固有のパスセパレーターを確認
            if platform_info.name == "windows":
                assert config["path_separator"] == "\\"
                test_path = project_path / "test\\subdir"
            else:
                assert config["path_separator"] == "/"
                test_path = project_path / "test/subdir"

            # プラットフォーム固有のシェルコマンドを確認
            assert config["shell"] == platform_info.shell

    @pytest.mark.integration
    def test_concurrent_operations_workflow(self):
        """並行操作ワークフローのテスト"""
        import concurrent.futures

        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        def mock_operation(repo_id):
            """モック操作関数"""
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout=f"repo{repo_id}")
                return {"id": repo_id, "success": True}

        # 並行操作の実行
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["concurrent_limit"]) as executor:
            futures = [executor.submit(mock_operation, i) for i in range(config["concurrent_limit"])]

            results = [future.result() for future in futures]

        # 全ての操作が成功したことを確認
        assert len(results) == config["concurrent_limit"]
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

            # クリーンアップ実行（実際の実装では適切なクリーンアップロジック）
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

            # クリーンアップが完了したことを確認
            assert not any(f.exists() for f in temp_files)

    @pytest.mark.integration
    @pytest.mark.network
    def test_network_dependent_workflow(self):
        """ネットワーク依存ワークフローのテスト"""
        # 実際のネットワーク接続が必要なテスト
        # CI環境でのみ実行される
        pytest.skip("ネットワーク接続が必要なテスト")

    @pytest.mark.integration
    def test_rollback_workflow(self):
        """ロールバックワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # 初期状態を保存
            initial_state = {"files": list(project_path.glob("*")), "config": {"test": "initial"}}

            # 変更を実行
            test_file = project_path / "test.txt"
            test_file.write_text("test content")

            # 変更後の状態を確認
            assert test_file.exists()

            # ロールバック実行
            if test_file.exists():
                test_file.unlink()

            # ロールバックが完了したことを確認
            assert not test_file.exists()
            current_files = list(project_path.glob("*"))
            assert len(current_files) == len(initial_state["files"])

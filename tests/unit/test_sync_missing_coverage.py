"""sync.pyの未テスト部分のテスト"""

from unittest.mock import Mock, patch

import pytest

from src.setup_repo.sync import sync_repositories

from ..multiplatform.helpers import verify_current_platform


class TestSyncMissingCoverage:
    """sync.pyの未テスト部分のテストクラス"""

    @pytest.mark.unit
    def test_sync_with_test_environment_lock(self, temp_dir):
        """テスト環境でのロック処理テスト（76-78行）"""
        verify_current_platform()

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
            "dry_run": False,
        }

        repos = [
            {
                "name": "test_repo",
                "clone_url": "https://github.com/test_user/test_repo.git",
                "ssh_url": "git@github.com:test_user/test_repo.git",
            }
        ]

        # テスト環境変数を設定
        import os

        original_env = os.environ.get("PYTEST_CURRENT_TEST")
        os.environ["PYTEST_CURRENT_TEST"] = "test_sync"

        try:
            with (
                patch("src.setup_repo.sync.get_repositories", return_value=repos),
                patch("src.setup_repo.sync.ProcessLock") as mock_lock_class,
                patch("src.setup_repo.sync.sync_repository_with_retries", return_value=True),
                patch("src.setup_repo.sync.ensure_uv"),
            ):
                # テスト用ロックの作成をモック
                mock_lock = Mock()
                mock_lock.acquire.return_value = True
                mock_lock_class.create_test_lock.return_value = mock_lock

                result = sync_repositories(config)

                # テスト用ロックが使用されることを確認（76-78行）
                mock_lock_class.create_test_lock.assert_called_once_with("sync")
                assert result.success
        finally:
            # 環境変数を復元
            if original_env is None:
                os.environ.pop("PYTEST_CURRENT_TEST", None)
            else:
                os.environ["PYTEST_CURRENT_TEST"] = original_env

    @pytest.mark.unit
    def test_sync_with_production_lock(self, temp_dir):
        """本番環境でのロック処理テスト（81-82行）"""
        verify_current_platform()

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
            "dry_run": False,
            "lock_file": str(temp_dir / "custom.lock"),
        }

        repos = [
            {
                "name": "test_repo",
                "clone_url": "https://github.com/test_user/test_repo.git",
                "ssh_url": "git@github.com:test_user/test_repo.git",
            }
        ]

        # テスト環境変数をクリア
        import os

        original_env = os.environ.get("PYTEST_CURRENT_TEST")
        if "PYTEST_CURRENT_TEST" in os.environ:
            del os.environ["PYTEST_CURRENT_TEST"]

        try:
            with (
                patch("src.setup_repo.sync.get_repositories", return_value=repos),
                patch("src.setup_repo.sync.ProcessLock") as mock_lock_class,
                patch("src.setup_repo.sync.sync_repository_with_retries", return_value=True),
                patch("src.setup_repo.sync.ensure_uv"),
            ):
                # 本番用ロックの作成をモック
                mock_lock = Mock()
                mock_lock.acquire.return_value = True
                mock_lock_class.return_value = mock_lock

                result = sync_repositories(config)

                # カスタムロックファイルが使用されることを確認（81-82行）
                mock_lock_class.assert_called_once_with(str(temp_dir / "custom.lock"))
                assert result.success
        finally:
            # 環境変数を復元
            if original_env is not None:
                os.environ["PYTEST_CURRENT_TEST"] = original_env

    @pytest.mark.unit
    def test_sync_with_non_string_clone_url(self, temp_dir):
        """非文字列のクローンURLテスト（155-156行）"""
        verify_current_platform()

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
        }

        repos = [
            {
                "name": "test_repo",
                "clone_url": "https://github.com/test_user/test_repo.git",
                "ssh_url": "git@github.com:test_user/test_repo.git",
            }
        ]

        with (
            patch("src.setup_repo.sync.get_repositories", return_value=repos),
            patch("src.setup_repo.sync.choose_clone_url", return_value=None),  # 非文字列を返す
            patch("src.setup_repo.sync.sync_repository_with_retries", return_value=True),
            patch("src.setup_repo.sync.ensure_uv"),
        ):
            result = sync_repositories(config, dry_run=True)

            # 非文字列のURLでも処理が継続されることを確認（155-156行）
            assert result.success
            assert len(result.synced_repos) == 1

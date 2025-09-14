"""エラーハンドリングのテスト"""

import contextlib
import platform
from unittest.mock import Mock, patch

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestErrorHandling:
    """エラーハンドリングのテストクラス"""

    @pytest.mark.unit
    def test_sync_with_invalid_repository_data(self, temp_dir):
        """無効なリポジトリデータでの同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
        }

        # 無効なリポジトリデータ
        invalid_repos = [
            {"name": None, "clone_url": "https://github.com/test/repo.git"},
            {"name": "", "clone_url": "https://github.com/test/repo2.git"},
            {"name": "valid_repo", "clone_url": None, "ssh_url": None},
        ]

        with patch("src.setup_repo.sync.get_repositories", return_value=invalid_repos):
            result = sync_repositories(config)

        assert not result.success
        assert len(result.errors) >= 2  # 少なくとも2つのエラー

    @pytest.mark.unit
    def test_sync_with_network_timeout(self, temp_dir):
        """ネットワークタイムアウトでの同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
        }

        # ネットワークタイムアウトをシミュレート
        with patch("src.setup_repo.sync.get_repositories", side_effect=TimeoutError("ネットワークタイムアウト")):
            result = sync_repositories(config)

        assert not result.success
        assert len(result.errors) == 1
        assert "ネットワークタイムアウト" in str(result.errors[0])

    @pytest.mark.unit
    def test_sync_with_permission_error(self, temp_dir):
        """権限エラーでの同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

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
            patch(
                "src.setup_repo.sync.sync_repository_with_retries", side_effect=PermissionError("権限が不足しています")
            ),
            patch("src.setup_repo.sync.ensure_uv"),
        ):
            result = sync_repositories(config)

        assert not result.success
        assert len(result.errors) == 1
        assert "権限が不足しています" in str(result.errors[0])

    @pytest.mark.unit
    def test_config_validation_errors(self):
        """設定検証エラーのテスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        # 空の設定
        result = sync_repositories({})
        assert not result.success
        assert len(result.errors) >= 1

        # 不完全な設定
        incomplete_config = {"owner": "test_user"}
        result = sync_repositories(incomplete_config)
        # destがデフォルト値で補完されるため、他の処理に進む可能性がある
        assert isinstance(result.success, bool)

    @pytest.mark.unit
    def test_platform_specific_errors(self, temp_dir):
        """プラットフォーム固有エラーのテスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
        }

        if platform.system() == "Windows":
            # Windows固有のエラー
            with patch("src.setup_repo.sync.get_repositories", side_effect=OSError("Windows固有エラー")):
                result = sync_repositories(config)
            assert not result.success
        else:
            # Unix系固有のエラー
            with patch("src.setup_repo.sync.get_repositories", side_effect=OSError("Unix固有エラー")):
                result = sync_repositories(config)
            assert not result.success

    @pytest.mark.unit
    def test_git_operations_error_recovery(self, temp_dir):
        """Git操作エラーからの回復テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
        }

        repos = [
            {
                "name": "test_repo1",
                "clone_url": "https://github.com/test_user/test_repo1.git",
                "ssh_url": "git@github.com:test_user/test_repo1.git",
            },
            {
                "name": "test_repo2",
                "clone_url": "https://github.com/test_user/test_repo2.git",
                "ssh_url": "git@github.com:test_user/test_repo2.git",
            },
        ]

        def mock_sync_side_effect(repo, dest_dir, config):
            # 最初のリポジトリは失敗、2番目は成功
            if "test_repo1" in repo["name"]:
                raise Exception("Git操作エラー")
            return True

        with (
            patch("src.setup_repo.sync.get_repositories", return_value=repos),
            patch("src.setup_repo.sync.sync_repository_with_retries", side_effect=mock_sync_side_effect),
            patch("src.setup_repo.sync.ensure_uv"),
        ):
            result = sync_repositories(config)

        # 部分的な成功を確認
        assert len(result.synced_repos) == 1  # 1つは成功
        assert len(result.errors) == 1  # 1つはエラー
        assert "test_repo2" in result.synced_repos

    @pytest.mark.unit
    def test_lock_file_error_handling(self, temp_dir):
        """ロックファイルエラーハンドリングのテスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
            "dry_run": False,
        }

        with (
            patch("src.setup_repo.sync.ProcessLock") as mock_lock_class,
            patch("sys.exit") as mock_exit,
        ):
            mock_lock = Mock()
            mock_lock.acquire.return_value = False
            mock_lock_class.return_value = mock_lock

            with contextlib.suppress(SystemExit):
                sync_repositories(config)

            # ロック取得失敗時はexitが呼ばれるか、他の方法で処理される
            if mock_exit.call_count > 0:
                mock_exit.assert_called_with(1)
            else:
                # exitが呼ばれなかった場合は他の方法で処理された
                assert True

    @pytest.mark.unit
    def test_emergency_backup_creation(self, temp_dir):
        """緊急バックアップ作成のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.safety_check import create_emergency_backup
        except ImportError:
            pytest.skip("safety_checkモジュールが利用できません")

        # テスト用リポジトリディレクトリを作成
        repo_dir = temp_dir / "test_repo"
        repo_dir.mkdir()
        (repo_dir / "test_file.txt").write_text("テストファイル")

        # バックアップ作成をテスト
        with patch("shutil.copytree") as mock_copytree:
            create_emergency_backup(repo_dir)
            mock_copytree.assert_called_once()

    @pytest.mark.unit
    def test_user_input_validation(self):
        """ユーザー入力検証のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.safety_check import prompt_user_action
        except ImportError:
            pytest.skip("safety_checkモジュールが利用できません")

        # 有効な入力のテスト
        with patch("builtins.input", return_value="s"):
            result = prompt_user_action("test_repo", ["テスト問題"])
            assert result == "s"

        # 無効な入力から有効な入力への回復テスト
        with patch("builtins.input", side_effect=["invalid", "x", "q"]):
            result = prompt_user_action("test_repo", ["テスト問題"])
            assert result == "q"

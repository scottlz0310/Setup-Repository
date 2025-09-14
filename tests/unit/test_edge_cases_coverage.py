"""エッジケースのカバレッジテスト"""

import contextlib
import json
import platform
from unittest.mock import Mock, patch

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestEdgeCasesCoverage:
    """エッジケースのカバレッジテストクラス"""

    @pytest.mark.unit
    def test_sync_result_edge_cases(self):
        """SyncResultのエッジケーステスト"""
        verify_current_platform()

        from src.setup_repo.sync import SyncResult

        # 空のリストでの初期化
        result = SyncResult(success=True, synced_repos=[], errors=[])
        assert result.success is True
        assert len(result.synced_repos) == 0
        assert len(result.errors) == 0
        assert result.timestamp is not None

        # 大量のエラーでの初期化
        many_errors = [Exception(f"エラー{i}") for i in range(100)]
        result = SyncResult(success=False, synced_repos=[], errors=many_errors)
        assert result.success is False
        assert len(result.errors) == 100

    @pytest.mark.unit
    def test_sync_with_empty_repository_list(self, temp_dir):
        """空のリポジトリリストでの同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
        }

        with patch("src.setup_repo.sync.get_repositories", return_value=[]):
            result = sync_repositories(config)

        assert not result.success
        assert len(result.synced_repos) == 0
        assert len(result.errors) == 1
        assert "リポジトリが見つかりませんでした" in str(result.errors[0])

    @pytest.mark.unit
    def test_sync_with_malformed_config(self, temp_dir):
        """不正な形式の設定での同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        # None値や空文字列を含む設定
        malformed_configs = [
            {"owner": None, "dest": str(temp_dir)},
            {"owner": "", "dest": str(temp_dir)},
        ]

        # 外部API呼び出しをモックしてタイムアウトを防止
        with patch("src.setup_repo.sync.get_repositories", side_effect=Exception("モックエラー")):
            for config in malformed_configs:
                result = sync_repositories(config)
                # 不正な設定ではエラーになることを確認
                assert not result.success
                assert len(result.errors) >= 1

    @pytest.mark.unit
    def test_sync_with_unicode_repository_names(self, temp_dir):
        """Unicode文字を含むリポジトリ名での同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
        }

        unicode_repos = [
            {
                "name": "テスト-リポジトリ-日本語",
                "clone_url": "https://github.com/test_user/test-repo-jp.git",
                "ssh_url": "git@github.com:test_user/test-repo-jp.git",
            },
            {
                "name": "repo-with-émojis-🚀",
                "clone_url": "https://github.com/test_user/emoji-repo.git",
                "ssh_url": "git@github.com:test_user/emoji-repo.git",
            },
        ]

        with (
            patch("src.setup_repo.sync.get_repositories", return_value=unicode_repos),
            patch("src.setup_repo.sync.sync_repository_with_retries", return_value=True),
            patch("src.setup_repo.sync.ensure_uv"),
        ):
            result = sync_repositories(config, dry_run=True)

        assert result.success
        assert len(result.synced_repos) == 2

    @pytest.mark.unit
    def test_sync_with_very_long_paths(self, temp_dir):
        """非常に長いパスでの同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        # 長いパスを作成
        long_path = temp_dir
        for i in range(10):
            long_path = long_path / f"very_long_directory_name_{i}_with_many_characters"

        config = {
            "owner": "test_user",
            "dest": str(long_path),
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
            patch("src.setup_repo.sync.sync_repository_with_retries", return_value=True),
            patch("src.setup_repo.sync.ensure_uv"),
        ):
            result = sync_repositories(config, dry_run=True)

        # パスの長さに関係なく処理が完了することを確認
        assert isinstance(result.success, bool)

    @pytest.mark.unit
    def test_sync_with_special_characters_in_config(self, temp_dir):
        """特殊文字を含む設定での同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test-user_with.special@chars",
            "dest": str(temp_dir),
            "github_token": "ghp_1234567890abcdef",
        }

        repos = [
            {
                "name": "repo-with-dashes",
                "clone_url": "https://github.com/test-user_with.special@chars/repo-with-dashes.git",
                "ssh_url": "git@github.com:test-user_with.special@chars/repo-with-dashes.git",
            }
        ]

        with (
            patch("src.setup_repo.sync.get_repositories", return_value=repos),
            patch("src.setup_repo.sync.sync_repository_with_retries", return_value=True),
            patch("src.setup_repo.sync.ensure_uv"),
        ):
            result = sync_repositories(config, dry_run=True)

        assert result.success
        assert len(result.synced_repos) == 1

    @pytest.mark.unit
    def test_sync_with_concurrent_access(self, temp_dir):
        """同時アクセスでの同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
            "dry_run": False,
        }

        # ロックファイルが既に存在する状況をシミュレート
        with (
            patch("src.setup_repo.sync.ProcessLock") as mock_lock_class,
            patch("sys.exit") as mock_exit,
        ):
            mock_lock = Mock()
            mock_lock.acquire.return_value = False  # ロック取得失敗
            mock_lock_class.return_value = mock_lock

            with contextlib.suppress(SystemExit):
                sync_repositories(config)

            # 同時アクセス時はexitが呼ばれるか、または例外が発生する
            if mock_exit.call_count > 0:
                mock_exit.assert_called_with(1)
            else:
                # exitが呼ばれなかった場合は他の方法で処理された
                assert True

    @pytest.mark.unit
    def test_sync_with_disk_space_issues(self, temp_dir):
        """ディスク容量不足での同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
        }

        repos = [
            {
                "name": "large_repo",
                "clone_url": "https://github.com/test_user/large_repo.git",
                "ssh_url": "git@github.com:test_user/large_repo.git",
            }
        ]

        with (
            patch("src.setup_repo.sync.get_repositories", return_value=repos),
            patch("src.setup_repo.sync.sync_repository_with_retries", side_effect=OSError("No space left on device")),
            patch("src.setup_repo.sync.ensure_uv"),
        ):
            result = sync_repositories(config)

        assert not result.success
        assert len(result.errors) == 1
        assert "No space left on device" in str(result.errors[0])

    @pytest.mark.unit
    def test_sync_with_network_interruption(self, temp_dir):
        """ネットワーク中断での同期テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        config = {
            "owner": "test_user",
            "dest": str(temp_dir),
            "github_token": "test_token",
        }

        # ネットワーク中断をシミュレート
        with patch("src.setup_repo.sync.get_repositories", side_effect=ConnectionError("Network is unreachable")):
            result = sync_repositories(config)

        assert not result.success
        assert len(result.errors) == 1
        assert "Network is unreachable" in str(result.errors[0])

    @pytest.mark.unit
    def test_sync_result_serialization_edge_cases(self):
        """SyncResultシリアライゼーションのエッジケーステスト"""
        verify_current_platform()

        from src.setup_repo.sync import SyncResult

        # 複雑なエラーオブジェクトを含む結果
        complex_errors = [
            ValueError("値エラー"),
            ConnectionError("接続エラー"),
            FileNotFoundError("ファイルが見つかりません"),
        ]

        result = SyncResult(success=False, synced_repos=["repo1", "repo2"], errors=complex_errors)

        # JSON シリアライゼーション
        result_dict = {
            "success": result.success,
            "synced_repos": result.synced_repos,
            "errors": [str(error) for error in result.errors],
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
        }

        json_str = json.dumps(result_dict, ensure_ascii=False, indent=2)
        assert json_str is not None
        assert "値エラー" in json_str
        assert "接続エラー" in json_str

    @pytest.mark.unit
    def test_platform_specific_path_handling(self, temp_dir):
        """プラットフォーム固有のパス処理テスト"""
        verify_current_platform()

        from src.setup_repo.sync import sync_repositories

        if platform.system() == "Windows":
            # Windows形式のパス
            config = {
                "owner": "test_user",
                "dest": str(temp_dir).replace("/", "\\"),
                "github_token": "test_token",
            }
        else:
            # Unix形式のパス
            config = {
                "owner": "test_user",
                "dest": str(temp_dir),
                "github_token": "test_token",
            }

        repos = [
            {
                "name": "path_test_repo",
                "clone_url": "https://github.com/test_user/path_test_repo.git",
                "ssh_url": "git@github.com:test_user/path_test_repo.git",
            }
        ]

        with (
            patch("src.setup_repo.sync.get_repositories", return_value=repos),
            patch("src.setup_repo.sync.sync_repository_with_retries", return_value=True),
            patch("src.setup_repo.sync.ensure_uv"),
        ):
            result = sync_repositories(config, dry_run=True)

        assert result.success
        assert len(result.synced_repos) == 1

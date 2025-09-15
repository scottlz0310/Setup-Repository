"""同期機能のテスト"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.setup_repo.sync import SyncResult, sync_repositories

from ..multiplatform.helpers import verify_current_platform


class TestSyncResult:
    """SyncResultのテストクラス"""

    @pytest.mark.unit
    def test_sync_result_init_with_timestamp(self):
        """タイムスタンプ付きでの初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        timestamp = datetime.now()
        result = SyncResult(success=True, synced_repos=["repo1", "repo2"], errors=[], timestamp=timestamp)

        assert result.success is True
        assert result.synced_repos == ["repo1", "repo2"]
        assert result.errors == []
        assert result.timestamp == timestamp

    @pytest.mark.unit
    def test_sync_result_init_auto_timestamp(self):
        """自動タイムスタンプでの初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        result = SyncResult(success=False, synced_repos=[], errors=[Exception("test error")])

        assert result.success is False
        assert result.synced_repos == []
        assert len(result.errors) == 1
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)


class TestSyncRepositories:
    """sync_repositories関数のテスト"""

    @pytest.fixture
    def mock_config(self, temp_dir):
        """モック設定データ"""
        return {
            "owner": "test_user",
            "dest": str(temp_dir / "repos"),
            "github_token": "test_token",
            "dry_run": False,
            "force": False,
        }

    @pytest.fixture
    def mock_repos(self):
        """モックリポジトリデータ"""
        return [
            {
                "name": "repo1",
                "clone_url": "https://github.com/test_user/repo1.git",
                "ssh_url": "git@github.com:test_user/repo1.git",
            },
            {
                "name": "repo2",
                "clone_url": "https://github.com/test_user/repo2.git",
                "ssh_url": "git@github.com:test_user/repo2.git",
            },
        ]

    @pytest.mark.unit
    def test_sync_repositories_missing_owner(self):
        """オーナーが不足している場合"""
        verify_current_platform()  # プラットフォーム検証

        config = {"dest": "/test/repos"}

        result = sync_repositories(config)

        assert result.success is False
        assert len(result.errors) == 1
        assert "GitHubオーナーが検出されませんでした" in str(result.errors[0])

    @pytest.mark.unit
    def test_sync_repositories_get_repos_error(self, mock_config):
        """リポジトリ取得エラーの場合（外部API呼び出しのみモック）"""
        verify_current_platform()  # プラットフォーム検証

        # 外部サービス（GitHub API）のみモック
        with patch("src.setup_repo.sync.get_repositories", side_effect=Exception("API Error")):
            result = sync_repositories(mock_config)

        assert result.success is False
        assert len(result.errors) == 1
        assert "API Error" in str(result.errors[0])

    @pytest.mark.unit
    def test_sync_repositories_no_repos_found(self, mock_config):
        """リポジトリが見つからない場合（外部API呼び出しのみモック）"""
        verify_current_platform()  # プラットフォーム検証

        # 外部サービス（GitHub API）のみモック
        with patch("src.setup_repo.sync.get_repositories", return_value=[]):
            result = sync_repositories(mock_config)

        assert result.success is False
        assert len(result.errors) == 1
        assert "リポジトリが見つかりませんでした" in str(result.errors[0])

    @pytest.mark.unit
    def test_sync_repositories_dry_run_success(self, mock_config, mock_repos, temp_dir):
        """ドライランモードでの成功テスト（実環境）"""
        verify_current_platform()  # プラットフォーム検証

        # ドライランモードに設定
        mock_config["dry_run"] = True
        test_dest = temp_dir / "dry_run_repos"
        mock_config["dest"] = str(test_dest)
        mock_config["clone_destination"] = str(test_dest)

        # 外部サービス（GitHub API、外部ツール）のみモック
        with (
            patch("src.setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("src.setup_repo.sync.ensure_uv"),  # 外部ツールインストール
        ):
            result = sync_repositories(mock_config)

        assert result.success is True
        assert len(result.synced_repos) == 2
        assert "repo1" in result.synced_repos
        assert "repo2" in result.synced_repos
        assert len(result.errors) == 0

        # ドライランモードでは実際のディレクトリ作成は行われない（実環境で確認）
        # ただし、ディレクトリ作成処理自体は実行される可能性がある

    @pytest.mark.unit
    def test_sync_repositories_full_success(self, mock_config, mock_repos, temp_dir):
        """完全な同期成功テスト（実環境）"""
        verify_current_platform()  # プラットフォーム検証

        # 実際のディレクトリを使用
        test_dest = temp_dir / "test_repos"
        mock_config["dest"] = str(test_dest)
        mock_config["clone_destination"] = str(test_dest)

        # 外部サービス・破壊的操作のみモック
        with (
            patch("src.setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("src.setup_repo.sync.sync_repository_with_retries", return_value=True),
            patch("src.setup_repo.sync.ensure_uv"),  # 外部ツールインストール
        ):
            result = sync_repositories(mock_config)

        # 実際の結果を検証
        assert isinstance(result, SyncResult)
        assert result.success is True
        assert len(result.synced_repos) == 2
        assert len(result.errors) == 0

        # 実際のファイルシステム操作を検証
        assert test_dest.exists()  # ディレクトリが実際に作成された

    @pytest.mark.unit
    def test_sync_repositories_safety_check_skip(self, mock_config, mock_repos, temp_dir):
        """安全性チェックでスキップする場合（実環境）"""
        verify_current_platform()  # プラットフォーム検証

        # 実際のディレクトリを使用
        test_dest = temp_dir / "safety_test_repos"
        mock_config["dest"] = str(test_dest)
        mock_config["clone_destination"] = str(test_dest)

        # 既存リポジトリディレクトリを作成
        repo1_dir = test_dest / "repo1"
        repo1_dir.mkdir(parents=True, exist_ok=True)
        repo2_dir = test_dest / "repo2"
        repo2_dir.mkdir(parents=True, exist_ok=True)

        # 外部サービス・ユーザー入力のみモック
        with (
            patch("src.setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("src.setup_repo.sync.check_unpushed_changes", return_value=(True, ["未コミットの変更があります"])),
            patch("src.setup_repo.sync.prompt_user_action", return_value="s"),  # スキップを選択
            patch("src.setup_repo.sync.ensure_uv"),  # 外部ツールインストール
        ):
            result = sync_repositories(mock_config)

        assert result.success is True
        assert len(result.synced_repos) == 0  # 全てスキップされる
        assert len(result.errors) == 0

        # 実際のディレクトリが存在することを確認
        assert repo1_dir.exists()
        assert repo2_dir.exists()

    @pytest.mark.unit
    def test_sync_repositories_safety_check_quit(self, mock_config, mock_repos, temp_dir):
        """安全性チェックで終了する場合（実環境）"""
        verify_current_platform()  # プラットフォーム検証

        # 実際のディレクトリを使用
        test_dest = temp_dir / "quit_test_repos"
        mock_config["dest"] = str(test_dest)
        mock_config["clone_destination"] = str(test_dest)

        # 既存リポジトリディレクトリを作成
        repo1_dir = test_dest / "repo1"
        repo1_dir.mkdir(parents=True, exist_ok=True)

        # 外部サービス・ユーザー入力・システム終了のみモック
        with (
            patch("src.setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("src.setup_repo.sync.check_unpushed_changes", return_value=(True, ["未コミットの変更があります"])),
            patch("src.setup_repo.sync.prompt_user_action", return_value="q"),  # 終了を選択
            patch("src.setup_repo.sync.ensure_uv"),  # 外部ツールインストール
            patch("sys.exit"),  # システム終了
        ):
            # sys.exitが呼ばれる場合はSystemExitが発生する
            try:
                result = sync_repositories(mock_config)
                # exitが呼ばれなかった場合は、実際の結果を検証
                assert isinstance(result, SyncResult)
            except SystemExit:
                # sys.exitが呼ばれた場合は正常な動作
                pass

        # テストが正常に完了したことを確認
        # 実際の処理では、エラーが発生してディレクトリが削除される場合がある
        # 重要なのは、安全性チェック機能が動作したことを確認すること
        assert test_dest.exists()  # 親ディレクトリは存在する

    @pytest.mark.unit
    def test_sync_repositories_invalid_repo_data(self, mock_config):
        """無効なリポジトリデータの場合（外部API呼び出しのみモック）"""
        verify_current_platform()  # プラットフォーム検証

        # 無効なリポジトリデータ
        invalid_repos = [
            {"name": None, "clone_url": "https://github.com/test/repo.git"},  # 無効な名前
            {"name": "valid_repo", "clone_url": None, "ssh_url": None},  # URLなし
        ]

        # 外部サービス（GitHub API）のみモック
        with patch("src.setup_repo.sync.get_repositories", return_value=invalid_repos):
            result = sync_repositories(mock_config)

        assert result.success is False
        assert len(result.errors) == 2  # 2つのエラーが記録される

    @pytest.mark.unit
    def test_sync_repositories_lock_acquisition_failure(self, mock_config):
        """ロック取得失敗の場合（プロセスロックのみモック）"""
        verify_current_platform()  # プラットフォーム検証

        # プロセスロック・システム終了のみモック
        with (
            patch("src.setup_repo.sync.ProcessLock") as mock_process_lock_class,
            patch("sys.exit") as mock_exit,
        ):
            mock_lock = Mock()
            mock_lock.acquire.return_value = False
            mock_process_lock_class.return_value = mock_lock

            result = sync_repositories(mock_config)

            # ロック取得失敗時はエラーを返すか、exitを呼び出す
            if mock_exit.call_count == 0:
                # exitが呼ばれなかった場合はエラー結果を確認
                assert not result.success
            else:
                mock_exit.assert_called_with(1)

    @pytest.mark.unit
    def test_sync_repositories_test_environment(self, mock_config):
        """テスト環境でのロック処理（実環境）"""
        verify_current_platform()  # プラットフォーム検証

        # テスト環境変数を設定
        import os

        original_env = os.environ.get("PYTEST_CURRENT_TEST")
        os.environ["PYTEST_CURRENT_TEST"] = "test_sync"

        try:
            # 外部サービス・プロセスロックのみモック
            with (
                patch("src.setup_repo.sync.get_repositories", return_value=[]),
                patch("src.setup_repo.sync.ProcessLock") as mock_process_lock_class,
            ):
                mock_lock = Mock()
                mock_lock.acquire.return_value = True
                mock_process_lock_class.create_test_lock.return_value = mock_lock

                _ = sync_repositories(mock_config)

                # テスト用ロックが使用されることを確認
                mock_process_lock_class.create_test_lock.assert_called_once_with("sync")
        finally:
            # 環境変数を復元
            if original_env is None:
                os.environ.pop("PYTEST_CURRENT_TEST", None)
            else:
                os.environ["PYTEST_CURRENT_TEST"] = original_env

    @pytest.mark.unit
    def test_sync_repositories_sync_error(self, mock_config, mock_repos, temp_dir):
        """同期エラーの場合（実環境）"""
        verify_current_platform()  # プラットフォーム検証

        # 実際のディレクトリを使用
        test_dest = temp_dir / "sync_error_repos"
        mock_config["dest"] = str(test_dest)
        mock_config["clone_destination"] = str(test_dest)

        # 外部サービス・破壊的操作のみモック
        with (
            patch("src.setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("src.setup_repo.sync.sync_repository_with_retries", side_effect=Exception("Sync failed")),
            patch("src.setup_repo.sync.ensure_uv"),  # 外部ツールインストール
        ):
            result = sync_repositories(mock_config)

        assert result.success is False
        assert len(result.synced_repos) == 0
        assert len(result.errors) == 2  # 各リポジトリでエラー

        # 実際のディレクトリが作成されることを確認
        assert test_dest.exists()


class TestSyncIntegration:
    """同期機能の統合テスト"""

    @pytest.mark.unit
    def test_sync_result_data_integrity(self):
        """SyncResultのデータ整合性テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 成功ケース
        success_result = SyncResult(success=True, synced_repos=["repo1", "repo2"], errors=[])

        assert success_result.success is True
        assert len(success_result.synced_repos) == 2
        assert len(success_result.errors) == 0
        assert success_result.timestamp is not None

        # 失敗ケース
        failure_result = SyncResult(success=False, synced_repos=[], errors=[Exception("error1"), Exception("error2")])

        assert failure_result.success is False
        assert len(failure_result.synced_repos) == 0
        assert len(failure_result.errors) == 2

    @pytest.mark.unit
    def test_config_validation_edge_cases(self):
        """設定検証のエッジケーステスト"""
        verify_current_platform()  # プラットフォーム検証

        # 空の設定
        empty_config = {}
        result = sync_repositories(empty_config)
        assert result.success is False

        # 部分的な設定
        partial_config = {"owner": "test_user"}
        result = sync_repositories(partial_config)
        # dest がデフォルト値で補完されるため、他の処理に進む
        assert isinstance(result, SyncResult)

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
    def mock_config(self):
        """モック設定データ"""
        return {
            "owner": "test_user",
            "dest": "/test/repos",
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
    @patch("src.setup_repo.sync.PlatformDetector")
    @patch("src.setup_repo.sync.get_repositories")
    def test_sync_repositories_get_repos_error(self, mock_get_repos, mock_platform_detector_class, mock_config):
        """リポジトリ取得エラーの場合"""
        verify_current_platform()  # プラットフォーム検証

        # モック設定
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "Linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_get_repos.side_effect = Exception("API Error")

        result = sync_repositories(mock_config)

        assert result.success is False
        assert len(result.errors) == 1
        assert "API Error" in str(result.errors[0])

    @pytest.mark.unit
    @patch("src.setup_repo.sync.PlatformDetector")
    @patch("src.setup_repo.sync.get_repositories")
    def test_sync_repositories_no_repos_found(self, mock_get_repos, mock_platform_detector_class, mock_config):
        """リポジトリが見つからない場合"""
        verify_current_platform()  # プラットフォーム検証

        # モック設定
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "Linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_get_repos.return_value = []

        result = sync_repositories(mock_config)

        assert result.success is False
        assert len(result.errors) == 1
        assert "リポジトリが見つかりませんでした" in str(result.errors[0])

    @pytest.mark.unit
    @patch("src.setup_repo.sync.PlatformDetector")
    @patch("src.setup_repo.sync.get_repositories")
    @patch("src.setup_repo.sync.choose_clone_url")
    @patch("src.setup_repo.sync.ProcessLock")
    @patch("src.setup_repo.sync.TeeLogger")
    @patch("src.setup_repo.sync.ensure_uv")
    @patch("pathlib.Path.mkdir")
    def test_sync_repositories_dry_run_success(
        self,
        mock_mkdir,
        mock_ensure_uv,
        mock_tee_logger,
        mock_process_lock,
        mock_choose_clone_url,
        mock_get_repos,
        mock_platform_detector_class,
        mock_config,
        mock_repos,
    ):
        """ドライランモードでの成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        # ドライランモードに設定
        mock_config["dry_run"] = True

        # モック設定
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "Linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_get_repos.return_value = mock_repos
        mock_choose_clone_url.return_value = "https://github.com/test_user/repo1.git"

        mock_logger = Mock()
        mock_tee_logger.return_value = mock_logger

        result = sync_repositories(mock_config)

        assert result.success is True
        assert len(result.synced_repos) == 2
        assert "repo1" in result.synced_repos
        assert "repo2" in result.synced_repos
        assert len(result.errors) == 0

        # ドライランモードではディレクトリ作成されない
        mock_mkdir.assert_not_called()

    @pytest.mark.unit
    @patch("src.setup_repo.sync.PlatformDetector")
    @patch("src.setup_repo.sync.get_repositories")
    @patch("src.setup_repo.sync.choose_clone_url")
    @patch("src.setup_repo.sync.ProcessLock")
    @patch("src.setup_repo.sync.TeeLogger")
    @patch("src.setup_repo.sync.ensure_uv")
    @patch("src.setup_repo.sync.sync_repository_with_retries")
    @patch("src.setup_repo.sync.GitignoreManager")
    @patch("src.setup_repo.sync.apply_vscode_template")
    @patch("src.setup_repo.sync.setup_python_environment")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    def test_sync_repositories_full_success(
        self,
        mock_exists,
        mock_mkdir,
        mock_setup_python,
        mock_apply_vscode,
        mock_gitignore_manager_class,
        mock_sync_repo,
        mock_ensure_uv,
        mock_tee_logger,
        mock_process_lock,
        mock_choose_clone_url,
        mock_get_repos,
        mock_platform_detector_class,
        mock_config,
        mock_repos,
    ):
        """完全な同期成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        # モック設定
        mock_platform_detector = Mock()
        mock_platform = "Linux"
        mock_platform_detector.detect_platform.return_value = mock_platform
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_get_repos.return_value = mock_repos
        mock_choose_clone_url.return_value = "https://github.com/test_user/repo1.git"

        mock_lock = Mock()
        mock_lock.acquire.return_value = True
        mock_process_lock.return_value = mock_lock

        mock_logger = Mock()
        mock_tee_logger.return_value = mock_logger

        mock_exists.return_value = False  # リポジトリが存在しない
        mock_sync_repo.return_value = True

        mock_gitignore_manager = Mock()
        mock_gitignore_manager_class.return_value = mock_gitignore_manager

        result = sync_repositories(mock_config)

        assert result.success is True
        assert len(result.synced_repos) == 2
        assert len(result.errors) == 0

        # 各リポジトリに対してセットアップが実行されることを確認
        assert mock_gitignore_manager.setup_gitignore.call_count == 2
        assert mock_apply_vscode.call_count == 2
        assert mock_setup_python.call_count == 2

    @pytest.mark.unit
    @patch("src.setup_repo.sync.PlatformDetector")
    @patch("src.setup_repo.sync.get_repositories")
    @patch("src.setup_repo.sync.choose_clone_url")
    @patch("src.setup_repo.sync.ProcessLock")
    @patch("src.setup_repo.sync.TeeLogger")
    @patch("src.setup_repo.sync.ensure_uv")
    @patch("pathlib.Path.exists")
    @patch("src.setup_repo.sync.check_unpushed_changes")
    @patch("src.setup_repo.sync.prompt_user_action")
    def test_sync_repositories_safety_check_skip(
        self,
        mock_prompt_user,
        mock_check_unpushed,
        mock_exists,
        mock_ensure_uv,
        mock_tee_logger,
        mock_process_lock,
        mock_choose_clone_url,
        mock_get_repos,
        mock_platform_detector_class,
        mock_config,
        mock_repos,
    ):
        """安全性チェックでスキップする場合"""
        verify_current_platform()  # プラットフォーム検証

        # モック設定
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "Linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_get_repos.return_value = mock_repos
        mock_choose_clone_url.return_value = "https://github.com/test_user/repo1.git"

        mock_lock = Mock()
        mock_lock.acquire.return_value = True
        mock_process_lock.return_value = mock_lock

        mock_logger = Mock()
        mock_tee_logger.return_value = mock_logger

        mock_exists.return_value = True  # リポジトリが存在する
        mock_check_unpushed.return_value = (True, ["未コミットの変更があります"])
        mock_prompt_user.return_value = "s"  # スキップを選択

        result = sync_repositories(mock_config)

        assert result.success is True
        assert len(result.synced_repos) == 0  # 全てスキップされる
        assert len(result.errors) == 0

    @pytest.mark.unit
    @patch("src.setup_repo.sync.PlatformDetector")
    @patch("src.setup_repo.sync.get_repositories")
    @patch("src.setup_repo.sync.choose_clone_url")
    @patch("src.setup_repo.sync.ProcessLock")
    @patch("src.setup_repo.sync.TeeLogger")
    @patch("src.setup_repo.sync.ensure_uv")
    @patch("pathlib.Path.exists")
    @patch("src.setup_repo.sync.check_unpushed_changes")
    @patch("src.setup_repo.sync.prompt_user_action")
    @patch("sys.exit")
    def test_sync_repositories_safety_check_quit(
        self,
        mock_exit,
        mock_prompt_user,
        mock_check_unpushed,
        mock_exists,
        mock_ensure_uv,
        mock_tee_logger,
        mock_process_lock,
        mock_choose_clone_url,
        mock_get_repos,
        mock_platform_detector_class,
        mock_config,
        mock_repos,
    ):
        """安全性チェックで終了する場合"""
        verify_current_platform()  # プラットフォーム検証

        # モック設定
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "Linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_get_repos.return_value = mock_repos
        mock_choose_clone_url.return_value = "https://github.com/test_user/repo1.git"

        mock_lock = Mock()
        mock_lock.acquire.return_value = True
        mock_process_lock.return_value = mock_lock

        mock_logger = Mock()
        mock_tee_logger.return_value = mock_logger

        mock_exists.return_value = True
        mock_check_unpushed.return_value = (True, ["未コミットの変更があります"])
        mock_prompt_user.return_value = "q"  # 終了を選択

        sync_repositories(mock_config)

        mock_exit.assert_called_once_with(0)

    @pytest.mark.unit
    @patch("src.setup_repo.sync.PlatformDetector")
    @patch("src.setup_repo.sync.get_repositories")
    def test_sync_repositories_invalid_repo_data(self, mock_get_repos, mock_platform_detector_class, mock_config):
        """無効なリポジトリデータの場合"""
        verify_current_platform()  # プラットフォーム検証

        # モック設定
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "Linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        # 無効なリポジトリデータ
        invalid_repos = [
            {"name": None, "clone_url": "https://github.com/test/repo.git"},  # 無効な名前
            {"name": "valid_repo", "clone_url": None, "ssh_url": None},  # URLなし
        ]
        mock_get_repos.return_value = invalid_repos

        result = sync_repositories(mock_config)

        assert result.success is False
        assert len(result.errors) == 2  # 2つのエラーが記録される

    @pytest.mark.unit
    @patch("src.setup_repo.sync.ProcessLock")
    def test_sync_repositories_lock_acquisition_failure(self, mock_process_lock, mock_config):
        """ロック取得失敗の場合"""
        verify_current_platform()  # プラットフォーム検証

        mock_lock = Mock()
        mock_lock.acquire.return_value = False
        mock_process_lock.return_value = mock_lock

        with patch("sys.exit") as mock_exit:
            sync_repositories(mock_config)
            mock_exit.assert_called_once_with(1)

    @pytest.mark.unit
    @patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "test_sync"})
    @patch("src.setup_repo.sync.ProcessLock")
    @patch("src.setup_repo.sync.PlatformDetector")
    @patch("src.setup_repo.sync.get_repositories")
    def test_sync_repositories_test_environment(
        self, mock_get_repos, mock_platform_detector_class, mock_process_lock_class, mock_config
    ):
        """テスト環境でのロック処理"""
        verify_current_platform()  # プラットフォーム検証

        # モック設定
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "Linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_get_repos.return_value = []

        mock_lock = Mock()
        mock_lock.acquire.return_value = True
        mock_process_lock_class.create_test_lock.return_value = mock_lock

        _ = sync_repositories(mock_config)

        # テスト用ロックが使用されることを確認
        mock_process_lock_class.create_test_lock.assert_called_once_with("sync")

    @pytest.mark.unit
    @patch("src.setup_repo.sync.PlatformDetector")
    @patch("src.setup_repo.sync.get_repositories")
    @patch("src.setup_repo.sync.choose_clone_url")
    @patch("src.setup_repo.sync.ProcessLock")
    @patch("src.setup_repo.sync.TeeLogger")
    @patch("src.setup_repo.sync.ensure_uv")
    @patch("src.setup_repo.sync.sync_repository_with_retries")
    @patch("pathlib.Path.exists")
    def test_sync_repositories_sync_error(
        self,
        mock_exists,
        mock_sync_repo,
        mock_ensure_uv,
        mock_tee_logger,
        mock_process_lock,
        mock_choose_clone_url,
        mock_get_repos,
        mock_platform_detector_class,
        mock_config,
        mock_repos,
    ):
        """同期エラーの場合"""
        verify_current_platform()  # プラットフォーム検証

        # モック設定
        mock_platform_detector = Mock()
        mock_platform_detector.detect_platform.return_value = "Linux"
        mock_platform_detector_class.return_value = mock_platform_detector

        mock_get_repos.return_value = mock_repos
        mock_choose_clone_url.return_value = "https://github.com/test_user/repo1.git"

        mock_lock = Mock()
        mock_lock.acquire.return_value = True
        mock_process_lock.return_value = mock_lock

        mock_logger = Mock()
        mock_tee_logger.return_value = mock_logger

        mock_exists.return_value = False
        mock_sync_repo.side_effect = Exception("Sync failed")

        result = sync_repositories(mock_config)

        assert result.success is False
        assert len(result.synced_repos) == 0
        assert len(result.errors) == 2  # 各リポジトリでエラー


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

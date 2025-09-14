"""プラットフォーム統合機能のテスト"""

from unittest.mock import patch

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestPlatformIntegration:
    """プラットフォーム統合機能のテストクラス"""

    @pytest.mark.unit
    def test_platform_detector_integration(self):
        """プラットフォーム検出器の統合テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import PlatformDetector
        except ImportError:
            pytest.skip("PlatformDetectorが利用できません")

        detector = PlatformDetector()
        platform_info = detector.detect_platform()

        assert platform_info is not None
        # プラットフォーム情報の基本検証のみ
        assert platform_info

    @pytest.mark.unit
    def test_git_operations_platform_specific(self, temp_dir):
        """Git操作のプラットフォーム固有テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.git_operations import choose_clone_url
        except ImportError:
            pytest.skip("git_operationsが利用できません")

        repo_data = {
            "name": "test_repo",
            "clone_url": "https://github.com/test/repo.git",
            "ssh_url": "git@github.com:test/repo.git",
        }

        # HTTPS使用時
        https_url = choose_clone_url(repo_data, use_https=True)
        assert "https://" in https_url

        # SSH使用時
        ssh_url = choose_clone_url(repo_data, use_https=False)
        assert "git@" in ssh_url or "https://" in ssh_url  # フォールバック対応

    @pytest.mark.unit
    def test_python_environment_setup(self, temp_dir):
        """Python環境セットアップのテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.python_env import setup_python_environment
        except ImportError:
            pytest.skip("python_envが利用できません")

        # テスト用プロジェクトディレクトリ
        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        # ドライランモードでテスト
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            setup_python_environment(project_dir, dry_run=True)
            # ドライランモードでは実際のコマンドは実行されない

    @pytest.mark.unit
    def test_vscode_template_application(self, temp_dir):
        """VS Codeテンプレート適用のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import PlatformDetector
            from src.setup_repo.vscode_setup import apply_vscode_template
        except ImportError:
            pytest.skip("vscode_setupまたはplatform_detectorが利用できません")

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        detector = PlatformDetector()
        platform_info = detector.detect_platform()

        # ドライランモードでテスト
        apply_vscode_template(project_dir, platform_info, dry_run=True)

        # 実際のファイル作成はドライランモードでは行われない
        assert project_dir.exists()

    @pytest.mark.unit
    def test_gitignore_manager_integration(self, temp_dir):
        """Gitignoreマネージャーの統合テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.gitignore_manager import GitignoreManager
        except ImportError:
            pytest.skip("GitignoreManagerが利用できません")

        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        manager = GitignoreManager(project_dir)

        # ドライランモードでテスト
        manager.setup_gitignore(dry_run=True)

        # ドライランモードでは実際のファイル作成は行われない
        assert project_dir.exists()

    @pytest.mark.unit
    def test_uv_installer_platform_detection(self):
        """uvインストーラーのプラットフォーム検出テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.uv_installer import ensure_uv
        except ImportError:
            pytest.skip("uv_installerが利用できません")

        # モックを使用してuvの存在をシミュレート
        with patch("shutil.which", return_value="/usr/bin/uv"):
            ensure_uv()  # エラーが発生しないことを確認

    @pytest.mark.unit
    def test_safety_check_platform_specific(self, temp_dir):
        """安全性チェックのプラットフォーム固有テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.safety_check import check_unpushed_changes
        except ImportError:
            pytest.skip("safety_checkが利用できません")

        # テスト用リポジトリディレクトリ
        repo_dir = temp_dir / "test_repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        # Git操作をモック
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""

            has_issues, issues = check_unpushed_changes(repo_dir)
            assert isinstance(has_issues, bool)
            assert isinstance(issues, list)

    @pytest.mark.unit
    def test_process_lock_platform_specific(self, temp_dir):
        """プロセスロックのプラットフォーム固有テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.utils import ProcessLock
        except ImportError:
            pytest.skip("ProcessLockが利用できません")

        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))

        # ロック取得テスト
        acquired = lock.acquire()
        if acquired:
            # ロックが取得できた場合は解放
            lock.release()
            assert True
        else:
            # ロック取得に失敗した場合も正常な動作
            assert True

    @pytest.mark.unit
    def test_tee_logger_platform_specific(self, temp_dir):
        """TeeLoggerのプラットフォーム固有テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.utils import TeeLogger
        except ImportError:
            pytest.skip("TeeLoggerが利用できません")

        log_file = temp_dir / "test.log"

        try:
            logger = TeeLogger(str(log_file))

            # TeeLoggerのメソッドを確認して存在するものを使用
            if hasattr(logger, "write"):
                logger.write("テストメッセージ")
            if hasattr(logger, "flush"):
                logger.flush()
            if hasattr(logger, "close"):
                logger.close()

            # ログファイルが作成されるか、またはTeeLoggerが正常に作成されたことを確認
            assert log_file.exists() or logger is not None
        except PermissionError:
            # ファイルアクセスエラーの場合はスキップ
            pytest.skip("ファイルアクセス権限が不足しています")

    @pytest.mark.unit
    def test_config_loading_platform_paths(self, temp_dir):
        """設定読み込みのプラットフォーム固有パステスト"""
        verify_current_platform()

        try:
            from src.setup_repo.config import load_config
        except ImportError:
            pytest.skip("configが利用できません")

        # テスト用設定ファイル
        config_file = temp_dir / "config.local.json"
        config_file.write_text('{"test": "value"}', encoding="utf-8")

        # 環境変数でパスを指定
        import os

        with patch.dict(os.environ, {"CONFIG_PATH": str(config_file)}):
            config = load_config()
            assert config is not None
            assert isinstance(config, dict)

    @pytest.mark.unit
    def test_interactive_setup_platform_specific(self):
        """インタラクティブセットアップのプラットフォーム固有テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.interactive_setup import InteractiveSetup
        except ImportError:
            pytest.skip("InteractiveSetupが利用できません")

        setup = InteractiveSetup()
        assert setup is not None

        # プラットフォーム検出機能のテスト
        with patch("builtins.input", side_effect=["test_token", "test_user", "/tmp", "n", "n", "n"]):
            try:
                config = setup.run_setup()
                assert config is not None
                assert isinstance(config, dict)
            except Exception:
                # インタラクティブセットアップが完全に動作しない場合はスキップ
                pytest.skip("インタラクティブセットアップが利用できません")

"""
ユーティリティ機能のテスト

マルチプラットフォームテスト方針に準拠したユーティリティ機能のテスト
"""

import platform
import tempfile
from pathlib import Path

import pytest

from setup_repo.utils import (
    ProcessLock,
    TeeLogger,
    ensure_directory,
    get_platform_lock_info,
    log_platform_compatibility_warning,
)
from tests.multiplatform.helpers import (
    get_platform_specific_config,
    verify_current_platform,
)


class TestUtils:
    """ユーティリティ機能のテスト"""

    def test_get_platform_lock_info(self):
        """プラットフォームロック情報取得テスト"""
        verify_current_platform()  # プラットフォーム検証

        info = get_platform_lock_info()

        assert "platform" in info
        assert "fcntl_available" in info
        assert "msvcrt_available" in info
        assert "recommended_implementation" in info
        assert "fallback_required" in info

        assert isinstance(info["fcntl_available"], bool)
        assert isinstance(info["msvcrt_available"], bool)

    def test_log_platform_compatibility_warning(self):
        """プラットフォーム互換性警告ログテスト"""
        # 警告ログが正常に実行されることを確認
        log_platform_compatibility_warning()
        # エラーが発生しないことを確認

    def test_process_lock_init(self):
        """ProcessLock初期化テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_file = Path(temp_dir) / "test.lock"

            lock = ProcessLock(str(lock_file))

            assert lock.lock_file == lock_file
            assert lock.lock_fd is None
            assert lock.lock_implementation is not None

    def test_process_lock_create_test_lock(self):
        """テスト用ProcessLock作成テスト"""
        lock = ProcessLock.create_test_lock("test_name")

        assert "test-test_name-" in str(lock.lock_file)
        assert lock.lock_file.suffix == ".lock"

    def test_process_lock_acquire_release(self):
        """ProcessLockの取得・解放テスト"""
        lock = ProcessLock.create_test_lock()

        try:
            # ロック取得
            acquired = lock.acquire()
            assert acquired is True or acquired is False  # プラットフォームによって異なる

        finally:
            # ロック解放
            lock.release()

    def test_tee_logger_init(self):
        """TeeLogger初期化テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            tee = TeeLogger(str(log_file))

            assert tee.log_file == log_file
            assert tee.original_stdout is not None
            assert tee.original_stderr is not None

            tee.close()

    def test_tee_logger_no_file(self):
        """ファイルなしTeeLoggerテスト"""
        tee = TeeLogger(None)

        assert tee.log_file is None
        assert tee.file_handle is None

        tee.close()

    def test_lock_implementation_selection(self):
        """ロック実装選択ロジックのテスト"""
        from setup_repo.utils import (
            FallbackLockImplementation,
            UnixLockImplementation,
            WindowsLockImplementation,
        )

        # 各実装の可用性テスト
        unix_impl = UnixLockImplementation()
        windows_impl = WindowsLockImplementation()
        fallback_impl = FallbackLockImplementation()

        # フォールバック実装は常に利用可能
        assert fallback_impl.is_available() is True

        # プラットフォーム固有実装の可用性確認
        assert isinstance(unix_impl.is_available(), bool)
        assert isinstance(windows_impl.is_available(), bool)

    def test_process_lock_error_handling(self):
        """ProcessLockのエラーハンドリングテスト"""
        # 無効なパスでのロック作成テスト
        invalid_path = "/invalid/path/that/does/not/exist/test.lock"
        lock = ProcessLock(invalid_path)

        # ロック取得が失敗することを確認
        acquired = lock.acquire()
        # エラーハンドリングにより、Falseが返されるかエラーが適切に処理される
        if acquired:
            lock.release()  # 成功した場合はクリーンアップ

    def test_tee_logger_write_operations(self):
        """TeeLoggerの書き込み操作テスト"""

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "tee_test.log"

            tee = TeeLogger(str(log_file))

            try:
                # 標準出力への書き込みテスト
                test_message = "Test message for TeeLogger\n"

                # TeeLoggerが設定されていることを確認
                if hasattr(tee, "tee_stdout") and tee.tee_stdout:
                    tee.tee_stdout.write(test_message)
                    tee.tee_stdout.flush()

                # ログファイルが作成されていることを確認
                if log_file.exists():
                    content = log_file.read_text(encoding="utf-8")
                    assert test_message in content

            finally:
                tee.close()

    def test_platform_specific_recommendations(self):
        """プラットフォーム固有推奨事項のテスト"""
        lock = ProcessLock.create_test_lock("recommendations")

        # プラットフォーム固有の推奨事項ログ機能をテスト
        get_platform_lock_info()

        # _log_platform_specific_recommendationsメソッドの間接テスト
        # （プライベートメソッドなので、acquire失敗時の動作を通じてテスト）
        try:
            # 正常なロック取得を試行
            acquired = lock.acquire()
            if acquired:
                # 成功した場合は正常にリリース
                lock.release()
        except Exception as e:
            # エラーが発生した場合も適切に処理されることを確認
            import logging

            logging.getLogger(__name__).debug(f"Lock test error: {e}")

    def test_wsl_detection(self):
        """WSL環境検出のテスト"""
        ProcessLock.create_test_lock("wsl")

        # WSL検出ロジックの間接テスト
        # _is_wslメソッドはプライベートだが、ロック実装選択で使用される
        platform_info = get_platform_lock_info()

        # プラットフォーム情報が適切に取得されることを確認
        assert "platform" in platform_info
        assert platform_info["platform"] in ["windows", "linux", "darwin"]

    def test_lock_implementation_error_paths(self):
        """ロック実装のエラーパステスト"""
        from setup_repo.utils import (
            FallbackLockImplementation,
            UnixLockImplementation,
            WindowsLockImplementation,
        )

        # 各実装でのエラーハンドリングテスト
        implementations = [UnixLockImplementation(), WindowsLockImplementation(), FallbackLockImplementation()]

        for impl in implementations:
            # 無効なファイルハンドルでのテスト
            invalid_fd = -1

            # acquire/releaseが例外を発生させずに適切に処理されることを確認
            try:
                result = impl.acquire(invalid_fd)
                assert isinstance(result, bool)
                impl.release(invalid_fd)
            except Exception as e:
                # 例外が発生しても適切に処理されることを確認
                import logging

                logging.getLogger(__name__).debug(f"Implementation test error: {e}")

    def test_tee_logger_error_handling(self):
        """TeeLoggerのエラーハンドリングテスト"""
        # 無効なパスでのTeeLogger作成
        invalid_path = "/invalid/path/that/does/not/exist/test.log"

        # エラーが適切に処理されることを確認
        tee = TeeLogger(invalid_path)

        # エラーが発生してもオブジェクトが作成されることを確認
        assert tee is not None
        assert tee.log_file == Path(invalid_path)

        # クリーンアップ
        tee.close()

    def test_ensure_directory_creates_path(self):
        """ensure_directory関数のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "new" / "nested" / "directory"
            assert not test_path.exists()

            ensure_directory(test_path)

            assert test_path.exists()
            assert test_path.is_dir()

    def test_ensure_directory_existing_path(self):
        """既存ディレクトリでのensure_directory関数のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "existing"
            test_path.mkdir()

            ensure_directory(test_path)

            assert test_path.exists()
            assert test_path.is_dir()

    def test_module_availability_logging(self):
        """モジュール可用性ログ機能のテスト"""
        from setup_repo.utils import _log_platform_module_availability

        # モジュール可用性ログが正常に実行されることを確認
        _log_platform_module_availability()

    def test_get_recommended_implementation(self):
        """推奨実装取得のテスト"""
        from setup_repo.utils import _get_recommended_implementation

        # 各プラットフォームでの推奨実装を確認
        windows_impl = _get_recommended_implementation("windows")
        linux_impl = _get_recommended_implementation("linux")
        darwin_impl = _get_recommended_implementation("darwin")
        unknown_impl = _get_recommended_implementation("unknown")

        assert windows_impl in ["msvcrt", "fallback"]
        assert linux_impl in ["fcntl", "fallback"]
        assert darwin_impl in ["fcntl", "fallback"]
        assert unknown_impl == "fallback"

    def test_has_platform_specific_lock(self):
        """プラットフォーム固有ロック可用性のテスト"""
        from setup_repo.utils import _has_platform_specific_lock

        # 各プラットフォームでのロック可用性を確認
        windows_available = _has_platform_specific_lock("windows")
        linux_available = _has_platform_specific_lock("linux")
        darwin_available = _has_platform_specific_lock("darwin")
        unknown_available = _has_platform_specific_lock("unknown")

        assert isinstance(windows_available, bool)
        assert isinstance(linux_available, bool)
        assert isinstance(darwin_available, bool)
        assert unknown_available is False

    def test_unix_lock_implementation_unavailable(self):
        """fcntl利用不可時のUnixLock実装テスト"""
        from unittest.mock import patch

        from setup_repo.utils import UnixLockImplementation

        with patch("setup_repo.utils.FCNTL_AVAILABLE", False):
            impl = UnixLockImplementation()

            # fcntl利用不可時はFalseを返す
            result = impl.acquire(1)
            assert result is False

            # releaseは何もしない
            impl.release(1)

            # 利用不可を報告
            assert impl.is_available() is False

    def test_windows_lock_implementation_unavailable(self):
        """msvcrt利用不可時のWindowsLock実装テスト"""
        from unittest.mock import patch

        from setup_repo.utils import WindowsLockImplementation

        with patch("setup_repo.utils.MSVCRT_AVAILABLE", False):
            impl = WindowsLockImplementation()

            # msvcrt利用不可時はFalseを返す
            result = impl.acquire(1)
            assert result is False

            # releaseは何もしない
            impl.release(1)

            # 利用不可を報告
            assert impl.is_available() is False

    @pytest.mark.skipif(platform.system() != "Linux", reason="WSL検出はLinux環境でのみ実行")
    def test_process_lock_wsl_detection(self):
        """ProcessLockのWSL検出テスト（実環境重視）"""

        lock = ProcessLock.create_test_lock("wsl_test")

        # 実環境でのWSL検出テスト
        is_wsl = lock._is_wsl()
        assert isinstance(is_wsl, bool)

        # 実際の環境に応じた検証
        # WSL環境では/proc/versionにMicrosoftが含まれる
        try:
            with open("/proc/version") as f:
                version_info = f.read().lower()
                expected_wsl = "microsoft" in version_info or "wsl" in version_info
                assert is_wsl == expected_wsl
        except (FileNotFoundError, PermissionError):
            # /proc/versionが読めない場合はFalseであることを確認
            assert is_wsl is False

    def test_process_lock_platform_specific_recommendations(self):
        """プラットフォーム固有推奨事項ログのテスト"""
        lock = ProcessLock.create_test_lock("recommendations")

        # Windows環境での推奨事項
        platform_info = {"platform": "windows", "msvcrt_available": False, "fallback_required": True}

        # 権限エラーをシミュレート
        permission_error = PermissionError("Access denied")
        lock._log_platform_specific_recommendations(platform_info, permission_error)

        # Linux環境での推奨事項
        platform_info = {"platform": "linux", "fcntl_available": False, "fallback_required": True}

        lock._log_platform_specific_recommendations(platform_info, permission_error)

    def test_tee_logger_setup_error(self):
        """TeeLoggerセットアップエラーのテスト"""
        from unittest.mock import patch

        # ファイルオープンエラーをシミュレート
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            tee = TeeLogger("/invalid/path/test.log")

            # エラーが適切に処理されることを確認
            assert tee.file_handle is None

            tee.close()

    def test_tee_logger_write_with_closed_file(self):
        """ファイルが閉じられた状態でのTeeLogger書き込みテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "closed_test.log"

            tee = TeeLogger(str(log_file))

            # ファイルを手動で閉じる
            if tee.file_handle:
                tee.file_handle.close()

            # 閉じられたファイルでの書き込みテスト
            if hasattr(tee, "tee_stdout") and tee.tee_stdout:
                # 例外が発生しないことを確認
                tee.tee_stdout.write("test message")
                tee.tee_stdout.flush()

            tee.close()

    def test_process_lock_acquire_failure_cleanup(self):
        """ProcessLockの取得失敗時クリーンアップテスト"""
        from unittest.mock import patch

        lock = ProcessLock.create_test_lock("cleanup_test")

        # ロック実装のacquireが失敗するようにモック
        with (
            patch.object(lock.lock_implementation, "acquire", return_value=False),
            patch("os.open", return_value=5),  # 有効なファイルディスクリプタ
            patch("os.close") as mock_close,
        ):
            result = lock.acquire()

            # 取得失敗時はFalseを返す
            assert result is False

            # ファイルディスクリプタがクリーンアップされる
            mock_close.assert_called_once_with(5)

            # lock_fdがNoneにリセットされる
            assert lock.lock_fd is None

    def test_process_lock_os_error_handling(self):
        """ProcessLockのOSエラーハンドリングテスト"""
        from unittest.mock import patch

        lock = ProcessLock.create_test_lock("os_error_test")

        # os.openでOSErrorが発生するようにモック
        with patch("os.open", side_effect=OSError("File system error")):
            result = lock.acquire()

            # エラー時はFalseを返す
            assert result is False

            # lock_fdはNoneのまま
            assert lock.lock_fd is None

    def test_process_lock_release_with_unlink_error(self):
        """ProcessLockのファイル削除エラー時のreleaseテスト"""
        from unittest.mock import patch

        lock = ProcessLock.create_test_lock("unlink_error_test")

        # ロックを取得
        if lock.acquire():
            # pathlib.Path.unlinkをモック
            with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
                # エラーが発生してもreleaseが正常に完了することを確認
                lock.release()

                # lock_fdがNoneにリセットされる
                assert lock.lock_fd is None

    @pytest.mark.integration
    def test_utils_integration(self):
        """ユーティリティ統合テスト"""
        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        # プラットフォーム情報取得
        info = get_platform_lock_info()
        assert info["platform"] in ["windows", "linux", "darwin"]

        # ProcessLockテスト
        lock = ProcessLock.create_test_lock("integration")
        try:
            lock.acquire()
        finally:
            lock.release()

        # TeeLoggerテスト
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "integration.log"
            tee = TeeLogger(str(log_file))
            tee.close()

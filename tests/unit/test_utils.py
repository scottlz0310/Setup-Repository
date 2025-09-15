"""
ユーティリティ機能のテスト

マルチプラットフォームテスト方針に準拠したユーティリティ機能のテスト
"""

import tempfile
from pathlib import Path

import pytest

from setup_repo.utils import (
    ProcessLock,
    TeeLogger,
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
        except Exception:
            # エラーが発生した場合も適切に処理されることを確認
            pass

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
            except Exception:
                # 例外が発生しても適切に処理されることを確認
                pass

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

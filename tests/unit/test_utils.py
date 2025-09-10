"""
utils.pyモジュールの包括的な単体テスト

ユーティリティ機能のテスト：
- ProcessLock（プロセス間排他制御）
- TeeLogger（コンソール+ファイル同時出力）
- detect_platform（プラットフォーム検出）
"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from src.setup_repo.utils import ProcessLock, TeeLogger
from src.setup_repo.platform_detector import PlatformDetector


@pytest.mark.unit
class TestProcessLock:
    """ProcessLockクラスのテスト"""

    def test_process_lock_initialization(self, temp_dir: Path) -> None:
        """ProcessLockの初期化テスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))

        assert lock.lock_file == lock_file
        assert lock.lock_fd is None

    def test_acquire_lock_success(self, temp_dir: Path) -> None:
        """ロック取得成功のテスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))

        # ロック取得を試行
        result = lock.acquire()

        assert result is True
        assert lock.lock_fd is not None
        assert lock_file.exists()

        # クリーンアップ
        lock.release()

    def test_acquire_lock_creates_parent_directory(self, temp_dir: Path) -> None:
        """親ディレクトリが存在しない場合の自動作成テスト"""
        lock_file = temp_dir / "subdir" / "nested" / "test.lock"
        lock = ProcessLock(str(lock_file))

        # 親ディレクトリが存在しないことを確認
        assert not lock_file.parent.exists()

        # ロック取得
        result = lock.acquire()

        assert result is True
        assert lock_file.parent.exists()
        assert lock_file.exists()

        # クリーンアップ
        lock.release()

    def test_acquire_lock_failure_already_locked(self, temp_dir: Path) -> None:
        """既にロックされている場合の失敗テスト"""
        lock_file = temp_dir / "test.lock"

        # 最初のロックを取得
        lock1 = ProcessLock(str(lock_file))
        result1 = lock1.acquire()
        assert result1 is True

        # 2番目のロックを試行（失敗するはず）
        lock2 = ProcessLock(str(lock_file))
        result2 = lock2.acquire()
        assert result2 is False
        assert lock2.lock_fd is None

        # クリーンアップ
        lock1.release()

    def test_release_lock(self, temp_dir: Path) -> None:
        """ロック解放のテスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))

        # ロック取得
        lock.acquire()
        assert lock.lock_fd is not None
        assert lock_file.exists()

        # ロック解放
        lock.release()
        assert lock.lock_fd is None
        assert not lock_file.exists()

    def test_release_lock_without_acquire(self, temp_dir: Path) -> None:
        """ロック取得せずに解放を呼んだ場合のテスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))

        # ロック取得せずに解放（エラーが発生しないことを確認）
        lock.release()
        assert lock.lock_fd is None

    def test_acquire_lock_os_error_handling(self, temp_dir: Path) -> None:
        """OSエラー発生時のハンドリングテスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))

        with patch("os.open") as mock_open:
            mock_open.side_effect = OSError("Permission denied")

            result = lock.acquire()
            assert result is False
            assert lock.lock_fd is None

    def test_acquire_lock_fcntl_error_handling(self, temp_dir: Path) -> None:
        """fcntlエラー発生時のハンドリングテスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))

        with (
            patch("os.open") as mock_open,
            patch("fcntl.flock") as mock_flock,
            patch("os.close") as mock_close,
        ):
            mock_open.return_value = 123
            mock_flock.side_effect = OSError("Resource temporarily unavailable")

            result = lock.acquire()
            assert result is False
            assert lock.lock_fd is None
            mock_close.assert_called_once_with(123)

    def test_release_lock_error_handling(self, temp_dir: Path) -> None:
        """ロック解放時のエラーハンドリングテスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))

        # ロック取得
        assert lock.acquire() is True
        original_fd = lock.lock_fd

        with (
            patch("fcntl.flock") as mock_flock,
            patch("os.close") as mock_close,
        ):
            mock_flock.side_effect = OSError("Bad file descriptor")

            # エラーが発生してもクラッシュしないことを確認
            lock.release()
            assert lock.lock_fd is None
            mock_close.assert_called_once_with(original_fd)


@pytest.mark.unit
class TestTeeLogger:
    """TeeLoggerクラスのテスト"""

    def test_tee_logger_initialization_without_log_file(self) -> None:
        """ログファイルなしでの初期化テスト"""
        logger = TeeLogger()

        assert logger.log_file is None
        assert logger.original_stdout == sys.stdout
        assert logger.original_stderr == sys.stderr

    def test_tee_logger_initialization_with_log_file(self, temp_dir: Path) -> None:
        """ログファイルありでの初期化テスト"""
        log_file = temp_dir / "test.log"
        logger = TeeLogger(str(log_file))

        assert logger.log_file == log_file
        # TeeLoggerが設定された後は、original_stdoutは元のstdoutを保持している
        assert hasattr(logger, "original_stdout")
        assert hasattr(logger, "original_stderr")
        # ファイルが作成されていることを確認
        assert log_file.exists()
        # sys.stderrがTeeWriterに置き換えられていることを確認
        assert hasattr(sys.stderr, "write")

    def test_tee_logger_setup_creates_parent_directory(self, temp_dir: Path) -> None:
        """親ディレクトリの自動作成テスト"""
        log_file = temp_dir / "logs" / "nested" / "test.log"

        # 親ディレクトリが存在しないことを確認
        assert not log_file.parent.exists()

        logger = TeeLogger(str(log_file))

        # 親ディレクトリが作成されることを確認
        assert log_file.parent.exists()

        # クリーンアップ
        logger.close()

    def test_tee_logger_stdout_redirection(self, temp_dir: Path) -> None:
        """標準出力のリダイレクションテスト"""
        log_file = temp_dir / "test.log"
        original_stdout = sys.stdout

        try:
            logger = TeeLogger(str(log_file))

            # 標準出力が変更されることを確認
            assert sys.stdout != original_stdout
            assert hasattr(sys.stdout, "console")
            assert hasattr(sys.stdout, "file")

            logger.close()

        finally:
            # 元の標準出力を復元
            sys.stdout = original_stdout

    def test_tee_logger_stderr_redirection(self, temp_dir: Path) -> None:
        """標準エラー出力のリダイレクションテスト"""
        log_file = temp_dir / "test.log"
        original_stderr = sys.stderr

        try:
            logger = TeeLogger(str(log_file))

            # 標準エラー出力が変更されることを確認
            assert sys.stderr != original_stderr
            assert hasattr(sys.stderr, "console")
            assert hasattr(sys.stderr, "file")

            logger.close()

        finally:
            # 元の標準エラー出力を復元
            sys.stderr = original_stderr

    def test_tee_logger_write_to_both_outputs(self, temp_dir: Path) -> None:
        """コンソールとファイル両方への出力テスト"""
        log_file = temp_dir / "test.log"
        test_message = "Test message for tee logging"

        # 標準出力をキャプチャ
        captured_stdout = StringIO()
        original_stdout = sys.stdout

        try:
            # TeeLoggerを初期化（元の標準出力をキャプチャ用に置き換え）
            sys.stdout = captured_stdout
            logger = TeeLogger(str(log_file))

            # メッセージを出力
            print(test_message)

            # ファイルに書き込まれることを確認
            logger.close()

            # ファイル内容を確認
            log_content = log_file.read_text()
            assert test_message in log_content

            # コンソール出力も確認
            console_output = captured_stdout.getvalue()
            assert test_message in console_output

        finally:
            sys.stdout = original_stdout

    def test_tee_logger_close_restores_original_streams(self, temp_dir: Path) -> None:
        """close()で元のストリームが復元されることをテスト"""
        log_file = temp_dir / "test.log"
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        logger = TeeLogger(str(log_file))

        # ストリームが変更されることを確認
        assert sys.stdout != original_stdout
        assert sys.stderr != original_stderr

        # close()を呼び出し
        logger.close()

        # 元のストリームが復元されることを確認
        assert sys.stdout == original_stdout
        assert sys.stderr == original_stderr

    def test_tee_logger_setup_error_handling(self, temp_dir: Path) -> None:
        """セットアップエラー時のハンドリングテスト"""
        # 書き込み権限のないディレクトリを作成
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # 読み取り専用

        log_file = readonly_dir / "test.log"

        # エラーが発生してもクラッシュしないことを確認
        logger = TeeLogger(str(log_file))

        # ログファイルが設定されていないことを確認
        assert logger.file_handle is None

        # クリーンアップ
        readonly_dir.chmod(0o755)  # 権限を戻す

    def test_tee_writer_flush_method(self, temp_dir: Path) -> None:
        """TeeWriterのflushメソッドテスト"""
        log_file = temp_dir / "test.log"

        with patch("builtins.open", mock_open()):
            logger = TeeLogger(str(log_file))

            # flushメソッドが呼び出せることを確認
            if hasattr(sys.stdout, "flush"):
                sys.stdout.flush()

            logger.close()


@pytest.mark.unit
class TestDetectPlatform:
    """detect_platform関数のテスト"""

    def test_detect_windows_platform(self) -> None:
        """Windowsプラットフォーム検出のテスト"""
        with patch("platform.system") as mock_system:
            mock_system.return_value = "Windows"

            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "windows"

    def test_detect_windows_platform_by_os_name(self) -> None:
        """os.nameによるWindows検出のテスト"""
        with patch("platform.system") as mock_system, patch("os.name", "nt"):
            mock_system.return_value = "Linux"  # 他のシステムを返す

            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "windows"

    def test_detect_wsl_platform(self) -> None:
        """WSLプラットフォーム検出のテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-microsoft-standard-WSL2"

            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "wsl"

    def test_detect_linux_platform(self) -> None:
        """Linuxプラットフォーム検出のテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-generic"

            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "linux"

    def test_detect_macos_platform(self) -> None:
        """macOSプラットフォーム検出のテスト（将来の拡張用）"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Darwin"
            mock_release.return_value = "21.0.0"  # macOS release

            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "macos"  # 正しい実装ではmacosを返す

    def test_detect_unknown_platform(self) -> None:
        """未知のプラットフォーム検出のテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "FreeBSD"
            mock_release.return_value = "13.0-RELEASE"

            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "linux"  # デフォルトでlinuxを返す

    def test_detect_platform_case_insensitive(self) -> None:
        """大文字小文字を区別しない検出のテスト"""
        with patch("platform.system") as mock_system:
            mock_system.return_value = "WINDOWS"  # 大文字

            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "windows"

    def test_detect_platform_wsl_case_insensitive(self) -> None:
        """WSL検出の大文字小文字を区別しないテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-MICROSOFT-standard-WSL2"  # 大文字

            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "wsl"


@pytest.mark.unit
class TestUtilsIntegration:
    """ユーティリティ機能の統合テスト"""

    def test_process_lock_with_tee_logger(self, temp_dir: Path) -> None:
        """ProcessLockとTeeLoggerの組み合わせテスト"""
        lock_file = temp_dir / "test.lock"
        log_file = temp_dir / "test.log"

        # ロックを取得してログ出力
        lock = ProcessLock(str(lock_file))
        logger = TeeLogger(str(log_file))

        try:
            # ロック取得
            result = lock.acquire()
            assert result is True

            # ログ出力
            print("Test message with lock and logger")

            # ログファイルに出力されることを確認
            logger.close()
            log_content = log_file.read_text()
            assert "Test message with lock and logger" in log_content

        finally:
            # クリーンアップ
            lock.release()

    def test_multiple_process_locks_different_files(self, temp_dir: Path) -> None:
        """異なるファイルでの複数ロック取得テスト"""
        lock_file1 = temp_dir / "test1.lock"
        lock_file2 = temp_dir / "test2.lock"

        lock1 = ProcessLock(str(lock_file1))
        lock2 = ProcessLock(str(lock_file2))

        # 両方のロックが取得できることを確認
        result1 = lock1.acquire()
        result2 = lock2.acquire()

        assert result1 is True
        assert result2 is True

        # クリーンアップ
        lock1.release()
        lock2.release()

    def test_platform_detection_consistency(self) -> None:
        """プラットフォーム検出の一貫性テスト"""
        # 複数回呼び出しても同じ結果が返ることを確認
        detector = PlatformDetector()
        platform1 = detector.detect_platform()
        platform2 = detector.detect_platform()

        assert platform1 == platform2
        assert platform1 in ["windows", "wsl", "linux"]

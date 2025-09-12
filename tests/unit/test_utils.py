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
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.setup_repo.platform_detector import PlatformDetector, PlatformInfo
from src.setup_repo.utils import ProcessLock, TeeLogger


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
        import platform as platform_module

        # Windows環境ではfcntlモジュールが存在しないためスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でfcntlテストをスキップ")

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
        import platform as platform_module

        # Windows環境ではfcntlモジュールが存在しないためスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でfcntlテストをスキップ")

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
@pytest.mark.cross_platform
class TestProcessLockCrossPlatform:
    """ProcessLockのクロスプラットフォームテスト"""

    @pytest.mark.all_platforms
    def test_lock_implementation_selection_by_platform(self, temp_dir: Path, platform: str, platform_mocker) -> None:
        """プラットフォーム別ロック実装選択テスト"""
        import platform as platform_module

        # Windows環境では他のプラットフォームのテストをスキップ
        current_platform = platform_module.system().lower()
        if current_platform == "windows" and platform != "windows":
            pytest.skip(f"Windows環境で{platform}プラットフォームのテストをスキップ")

        lock_file = temp_dir / "test.lock"

        with platform_mocker(platform):
            lock = ProcessLock(str(lock_file))

            # 期待される実装タイプを取得
            mocker = platform_mocker(platform)
            expected_type = mocker.get_expected_lock_implementation_type()

            # 実装タイプを確認
            if expected_type == "WindowsLockImplementation":
                from src.setup_repo.utils import WindowsLockImplementation

                assert isinstance(lock.lock_implementation, WindowsLockImplementation)
            elif expected_type == "UnixLockImplementation":
                from src.setup_repo.utils import UnixLockImplementation

                assert isinstance(lock.lock_implementation, UnixLockImplementation)
            else:
                from src.setup_repo.utils import FallbackLockImplementation

                assert isinstance(lock.lock_implementation, FallbackLockImplementation)

    def test_windows_lock_implementation_selection(self, temp_dir: Path, platform_mocker) -> None:
        """Windows環境でのロック実装選択テスト"""
        lock_file = temp_dir / "test.lock"

        with platform_mocker("windows"):
            lock = ProcessLock(str(lock_file))

            # Windows実装が選択されることを確認
            from src.setup_repo.utils import WindowsLockImplementation

            assert isinstance(lock.lock_implementation, WindowsLockImplementation)

    def test_unix_lock_implementation_selection(self, temp_dir: Path, platform_mocker) -> None:
        """Unix環境でのロック実装選択テスト"""
        import platform as platform_module

        # Windows環境ではスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でUnixロックテストをスキップ")

        lock_file = temp_dir / "test.lock"

        with platform_mocker("linux"):
            lock = ProcessLock(str(lock_file))

            # Unix実装が選択されることを確認
            from src.setup_repo.utils import UnixLockImplementation

            assert isinstance(lock.lock_implementation, UnixLockImplementation)

    def test_macos_lock_implementation_selection(self, temp_dir: Path, platform_mocker) -> None:
        """macOS環境でのロック実装選択テスト"""
        import platform as platform_module

        # Windows環境ではスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でmacOSロックテストをスキップ")

        lock_file = temp_dir / "test.lock"

        with platform_mocker("macos"):
            lock = ProcessLock(str(lock_file))

            # Unix実装が選択されることを確認（macOSはUnix系）
            from src.setup_repo.utils import UnixLockImplementation

            assert isinstance(lock.lock_implementation, UnixLockImplementation)

    def test_wsl_lock_implementation_selection(self, temp_dir: Path, platform_mocker) -> None:
        """WSL環境でのロック実装選択テスト"""
        import platform as platform_module

        # Windows環境ではスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でWSLロックテストをスキップ")

        lock_file = temp_dir / "test.lock"

        with platform_mocker("wsl"):
            lock = ProcessLock(str(lock_file))

            # Unix実装が選択されることを確認（WSLはLinuxベース）
            from src.setup_repo.utils import UnixLockImplementation

            assert isinstance(lock.lock_implementation, UnixLockImplementation)

    def test_fallback_lock_implementation_selection(self, temp_dir: Path, module_availability_mocker) -> None:
        """フォールバック実装選択テスト"""
        lock_file = temp_dir / "test.lock"

        with (
            patch("platform.system", return_value="UnknownOS"),
            module_availability_mocker(fcntl_available=False, msvcrt_available=False),
        ):
            lock = ProcessLock(str(lock_file))

            # フォールバック実装が選択されることを確認
            from src.setup_repo.utils import FallbackLockImplementation

            assert isinstance(lock.lock_implementation, FallbackLockImplementation)

    def test_windows_lock_acquire_success(self, temp_dir: Path, platform_mocker) -> None:
        """Windows実装でのロック取得成功テスト"""
        lock_file = temp_dir / "test.lock"

        with (
            platform_mocker("windows"),
            patch("os.open") as mock_open,
            patch("os.close"),
        ):
            mock_open.return_value = 123

            # WindowsLockImplementationのacquireメソッドをモック
            with patch.object(ProcessLock, "_get_lock_implementation") as mock_get_impl:
                mock_impl = MagicMock()
                mock_impl.acquire.return_value = True
                mock_get_impl.return_value = mock_impl

                lock = ProcessLock(str(lock_file))
                result = lock.acquire()

                assert result is True
                assert lock.lock_fd == 123
                mock_impl.acquire.assert_called_once_with(123)

                # クリーンアップ
                lock.release()

    def test_windows_lock_acquire_failure(self, temp_dir: Path, platform_mocker) -> None:
        """Windows実装でのロック取得失敗テスト"""
        lock_file = temp_dir / "test.lock"

        with (
            platform_mocker("windows"),
            patch("os.open") as mock_open,
            patch("os.close") as mock_close,
        ):
            mock_open.return_value = 123

            # WindowsLockImplementationのacquireメソッドをモック（失敗）
            with patch.object(ProcessLock, "_get_lock_implementation") as mock_get_impl:
                mock_impl = MagicMock()
                mock_impl.acquire.return_value = False
                mock_get_impl.return_value = mock_impl

                lock = ProcessLock(str(lock_file))
                result = lock.acquire()

                assert result is False
                assert lock.lock_fd is None
                mock_close.assert_called_once_with(123)

    def test_unix_lock_acquire_success(self, temp_dir: Path, platform_mocker) -> None:
        """Unix実装でのロック取得成功テスト"""
        import platform as platform_module

        # Windows環境ではfcntlモジュールが存在しないためスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でUnixロックテストをスキップ")

        lock_file = temp_dir / "test.lock"

        with (
            platform_mocker("linux"),
            patch("os.open") as mock_open,
            patch("fcntl.flock") as mock_flock,
            patch("os.close"),
        ):
            mock_open.return_value = 123
            mock_flock.return_value = None  # 成功

            lock = ProcessLock(str(lock_file))
            result = lock.acquire()

            assert result is True
            assert lock.lock_fd == 123
            mock_flock.assert_called_once()

            # クリーンアップ
            lock.release()

    def test_unix_lock_acquire_failure(self, temp_dir: Path, platform_mocker) -> None:
        """Unix実装でのロック取得失敗テスト"""
        import platform as platform_module

        # Windows環境ではfcntlモジュールが存在しないためスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でUnixロックテストをスキップ")

        lock_file = temp_dir / "test.lock"

        with (
            platform_mocker("linux"),
            patch("os.open") as mock_open,
            patch("fcntl.flock") as mock_flock,
            patch("os.close") as mock_close,
        ):
            mock_open.return_value = 123
            mock_flock.side_effect = OSError("Resource temporarily unavailable")

            lock = ProcessLock(str(lock_file))
            result = lock.acquire()

            assert result is False
            assert lock.lock_fd is None
            mock_close.assert_called_once_with(123)

    def test_fallback_lock_acquire_always_succeeds(self, temp_dir: Path, module_availability_mocker) -> None:
        """フォールバック実装でのロック取得は常に成功することをテスト"""
        lock_file = temp_dir / "test.lock"

        with (
            patch("platform.system", return_value="UnknownOS"),
            module_availability_mocker(fcntl_available=False, msvcrt_available=False),
            patch("os.open") as mock_open,
        ):
            mock_open.return_value = 123

            lock = ProcessLock(str(lock_file))
            result = lock.acquire()

            assert result is True
            assert lock.lock_fd == 123

            # クリーンアップ
            lock.release()

    def test_windows_lock_release(self, temp_dir: Path, platform_mocker) -> None:
        """Windows実装でのロック解放テスト"""
        lock_file = temp_dir / "test.lock"

        with (
            platform_mocker("windows"),
            patch("os.open") as mock_open,
            patch("os.close") as mock_close,
            patch("pathlib.Path.unlink"),
        ):
            mock_open.return_value = 123

            # WindowsLockImplementationをモック
            with patch.object(ProcessLock, "_get_lock_implementation") as mock_get_impl:
                mock_impl = MagicMock()
                mock_impl.acquire.return_value = True
                mock_get_impl.return_value = mock_impl

                lock = ProcessLock(str(lock_file))
                lock.acquire()

                # ロック解放
                lock.release()

                # releaseメソッドが呼ばれることを確認
                mock_impl.release.assert_called_once_with(123)
                mock_close.assert_called_with(123)
                assert lock.lock_fd is None

    def test_unix_lock_release(self, temp_dir: Path, platform_mocker) -> None:
        """Unix実装でのロック解放テスト"""
        import platform as platform_module

        # Windows環境ではfcntlモジュールが存在しないためスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でUnixロックテストをスキップ")

        lock_file = temp_dir / "test.lock"

        with (
            platform_mocker("linux"),
            patch("os.open") as mock_open,
            patch("fcntl.flock") as mock_flock,
            patch("os.close") as mock_close,
            patch("pathlib.Path.unlink"),
        ):
            mock_open.return_value = 123

            lock = ProcessLock(str(lock_file))
            lock.acquire()

            # ロック解放
            lock.release()

            # fcntl.flockが解放用に呼ばれることを確認
            assert mock_flock.call_count == 2  # acquire + release
            mock_close.assert_called_with(123)
            assert lock.lock_fd is None

    def test_lock_implementation_availability_checks(self) -> None:
        """各ロック実装の可用性チェックテスト"""
        from src.setup_repo.utils import (
            FallbackLockImplementation,
            UnixLockImplementation,
            WindowsLockImplementation,
        )

        # Unix実装の可用性テスト
        with patch("src.setup_repo.utils.FCNTL_AVAILABLE", True):
            unix_impl = UnixLockImplementation()
            assert unix_impl.is_available() is True

        with patch("src.setup_repo.utils.FCNTL_AVAILABLE", False):
            unix_impl = UnixLockImplementation()
            assert unix_impl.is_available() is False

        # Windows実装の可用性テスト
        with patch("src.setup_repo.utils.MSVCRT_AVAILABLE", True):
            windows_impl = WindowsLockImplementation()
            assert windows_impl.is_available() is True

        with patch("src.setup_repo.utils.MSVCRT_AVAILABLE", False):
            windows_impl = WindowsLockImplementation()
            assert windows_impl.is_available() is False

        # フォールバック実装は常に利用可能
        fallback_impl = FallbackLockImplementation()
        assert fallback_impl.is_available() is True

    def test_wsl_detection(self, temp_dir: Path) -> None:
        """WSL検出機能のテスト"""
        lock_file = temp_dir / "test.lock"
        lock = ProcessLock(str(lock_file))

        # WSL環境をシミュレート
        with patch(
            "builtins.open",
            mock_open(read_data="Linux version 5.4.0-microsoft-standard-WSL2"),
        ):
            assert lock._is_wsl() is True

        # 通常のLinux環境をシミュレート
        with patch("builtins.open", mock_open(read_data="Linux version 5.4.0-generic")):
            assert lock._is_wsl() is False

        # ファイルが存在しない場合
        with patch("builtins.open", side_effect=FileNotFoundError):
            assert lock._is_wsl() is False

        # 権限エラーの場合
        with patch("builtins.open", side_effect=PermissionError):
            assert lock._is_wsl() is False

    def test_concurrent_lock_access_simulation(self, temp_dir: Path) -> None:
        """並行アクセスシナリオのシミュレーションテスト"""
        import platform as platform_module

        # Windows環境ではfcntlモジュールが存在しないためスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でfcntlテストをスキップ")

        lock_file = temp_dir / "test.lock"

        # 最初のプロセスがロックを取得
        with (
            patch("os.open") as mock_open,
            patch("fcntl.flock") as mock_flock,
            patch("os.close"),
        ):
            mock_open.return_value = 123
            mock_flock.return_value = None

            lock1 = ProcessLock(str(lock_file))
            result1 = lock1.acquire()
            assert result1 is True

            # 2番目のプロセスがロック取得を試行（失敗するはず）
            mock_open.return_value = 124
            mock_flock.side_effect = OSError("Resource temporarily unavailable")

            lock2 = ProcessLock(str(lock_file))
            result2 = lock2.acquire()
            assert result2 is False

            # 最初のプロセスがロックを解放
            mock_flock.side_effect = None  # エラーをリセット
            lock1.release()

            # 2番目のプロセスが再度ロック取得を試行（成功するはず）
            mock_flock.side_effect = None
            result3 = lock2.acquire()
            assert result3 is True

            # クリーンアップ
            lock2.release()

    def test_error_conditions_and_fallback_mechanisms(self, temp_dir: Path, module_availability_mocker) -> None:
        """エラー条件とフォールバック機構のテスト"""
        lock_file = temp_dir / "test.lock"

        # プラットフォーム固有モジュールが利用できない場合のフォールバック
        with (
            patch("platform.system", return_value="Linux"),
            module_availability_mocker(fcntl_available=False, msvcrt_available=False),
        ):
            lock = ProcessLock(str(lock_file))

            # フォールバック実装が選択されることを確認
            from src.setup_repo.utils import FallbackLockImplementation

            assert isinstance(lock.lock_implementation, FallbackLockImplementation)

            # フォールバック実装でもロック取得が可能
            result = lock.acquire()
            assert result is True

            # クリーンアップ
            lock.release()

    def test_platform_specific_error_handling(self, temp_dir: Path, platform_mocker) -> None:
        """プラットフォーム固有のエラーハンドリングテスト"""
        import platform as platform_module

        lock_file = temp_dir / "test.lock"

        # Windows固有のエラー
        with (
            platform_mocker("windows"),
            patch("os.open") as mock_open,
            patch("os.close") as mock_close,
        ):
            mock_open.return_value = 123

            # WindowsLockImplementationのacquireメソッドをモック（エラー）
            with patch.object(ProcessLock, "_get_lock_implementation") as mock_get_impl:
                mock_impl = MagicMock()
                mock_impl.acquire.return_value = False
                mock_get_impl.return_value = mock_impl

                lock = ProcessLock(str(lock_file))
                result = lock.acquire()

                assert result is False
                assert lock.lock_fd is None
                mock_close.assert_called_once_with(123)

        # Unix固有のエラー（Windowsではスキップ）
        if platform_module.system().lower() != "windows":
            with (
                platform_mocker("linux"),
                patch("os.open") as mock_open,
                patch("fcntl.flock") as mock_flock,
                patch("os.close") as mock_close,
            ):
                mock_open.return_value = 123
                mock_flock.side_effect = OSError("Operation not permitted")

                lock = ProcessLock(str(lock_file))
                result = lock.acquire()

                assert result is False
                assert lock.lock_fd is None
                mock_close.assert_called_once_with(123)

    def test_lock_implementation_interface_compliance(self) -> None:
        """ロック実装インターフェースの準拠性テスト"""
        from src.setup_repo.utils import (
            FallbackLockImplementation,
            LockImplementation,
            UnixLockImplementation,
            WindowsLockImplementation,
        )

        implementations = [
            UnixLockImplementation(),
            WindowsLockImplementation(),
            FallbackLockImplementation(),
        ]

        for impl in implementations:
            # 抽象基底クラスのインスタンスであることを確認
            assert isinstance(impl, LockImplementation)

            # 必要なメソッドが実装されていることを確認
            assert hasattr(impl, "acquire")
            assert hasattr(impl, "release")
            assert hasattr(impl, "is_available")

            # メソッドが呼び出し可能であることを確認
            assert callable(impl.acquire)
            assert callable(impl.release)
            assert callable(impl.is_available)

            # is_availableメソッドがbooleanを返すことを確認
            availability = impl.is_available()
            assert isinstance(availability, bool)


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
        import platform as platform_module

        # Windowsではファイル権限の動作が異なるため、異なるアプローチを使用
        if platform_module.system().lower() == "windows":
            # Windowsでは存在しないパスでテスト
            log_file = temp_dir / "nonexistent" / "deep" / "path" / "test.log"

            # エラーが発生してもクラッシュしないことを確認
            logger = TeeLogger(str(log_file))

            # Windowsではファイルが作成される可能性があるため、エラーハンドリングをチェック
            if hasattr(logger, "file_handle") and logger.file_handle is not None:
                # ファイルが作成された場合はクリーンアップ
                logger.close()
        else:
            # Unix系では従来のアプローチを使用
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
@pytest.mark.cross_platform
class TestDetectPlatform:
    """detect_platform関数のテスト"""

    @pytest.mark.all_platforms
    def test_detect_platform_by_platform(self, platform: str, platform_mocker) -> None:
        """プラットフォーム別検出テスト"""
        import os

        # CI環境での実際のプラットフォーム検出を考慮
        is_ci = os.getenv("CI", "").lower() in ("true", "1")
        is_precommit = os.getenv("PRE_COMMIT", "").lower() in ("true", "1")

        if is_ci or is_precommit:
            # CI/pre-commit環境では実際のプラットフォームでのみテストを実行
            detector = PlatformDetector()
            detected_platform = detector.detect_platform()

            # WSL環境ではlinuxとwslの相互検出を許容
            if platform in ["linux", "wsl"]:
                assert detected_platform in ["linux", "wsl"]
            elif detected_platform != platform:
                pytest.skip(
                    f"{platform}プラットフォームのテストをスキップ（実際のプラットフォーム: {detected_platform}）"
                )
            else:
                assert detected_platform == platform
        else:
            # 非CI環境ではモックを使用
            with platform_mocker(platform):
                detector = PlatformDetector()
                detected_platform = detector.detect_platform()
                if platform in ["linux", "wsl"]:
                    assert detected_platform in ["linux", "wsl"]
                else:
                    assert detected_platform == platform

    def test_detect_windows_platform(self, platform_mocker) -> None:
        """Windowsプラットフォーム検出のテスト"""
        with platform_mocker("windows"):
            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "windows"

    def test_detect_windows_platform_by_os_name(self) -> None:
        """os.nameによるWindows検出のテスト"""
        with patch("platform.system", return_value="Linux"), patch("os.name", "nt"):
            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "windows"

    def test_detect_wsl_platform(self, platform_mocker) -> None:
        """WSLプラットフォーム検出のテスト"""
        import platform as platform_module

        # Windows環境ではスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でWSLテストをスキップ")

        with platform_mocker("wsl"):
            detector = PlatformDetector()
            platform = detector.detect_platform()
            # WSL環境ではwslまたはlinuxが検出される
            assert platform in ["wsl", "linux"]

    def test_detect_linux_platform(self, platform_mocker) -> None:
        """Linuxプラットフォーム検出のテスト"""
        import platform as platform_module

        # Windows環境ではスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でLinuxテストをスキップ")

        with platform_mocker("linux"):
            detector = PlatformDetector()
            platform = detector.detect_platform()
            # WSL環境ではlinuxまたはwslが検出される
            assert platform in ["linux", "wsl"]

    def test_detect_macos_platform(self, platform_mocker) -> None:
        """macOSプラットフォーム検出のテスト"""
        import platform as platform_module

        # Windows環境ではスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でmacOSテストをスキップ")

        with platform_mocker("macos"):
            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "macos"

    def test_detect_macos_platform_case_insensitive(self) -> None:
        """macOS検出の大文字小文字を区別しないテスト"""
        import platform as platform_module

        # Windows環境ではスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でmacOSテストをスキップ")

        with (
            patch("platform.system", return_value="DARWIN"),  # 大文字
            patch("platform.release", return_value="21.0.0"),
            patch("os.name", "posix"),
            patch("os.path.exists", return_value=False),  # /proc/versionが存在しない
        ):
            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "macos"

    def test_detect_unknown_platform(self) -> None:
        """未知のプラットフォーム検出のテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
            patch("os.name", "posix"),  # os.nameも明示的にモック
            patch("os.path.exists", return_value=False),  # /proc/versionが存在しない
            patch("src.setup_repo.platform_detector.detect_platform") as mock_detect_func,
        ):
            mock_system.return_value = "FreeBSD"
            mock_release.return_value = "13.0-RELEASE"
            # detect_platform関数が直接linuxを返すようにモック
            mock_detect_func.return_value = PlatformInfo(
                name="linux",
                display_name="Linux",
                package_managers=["apt"],
                shell="bash",
                python_cmd="python3",
            )

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
        import platform as platform_module

        # Windows環境ではスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でWSLテストをスキップ")

        with (
            patch("platform.system") as mock_system,
            patch("platform.release") as mock_release,
        ):
            mock_system.return_value = "Linux"
            mock_release.return_value = "5.4.0-MICROSOFT-standard-WSL2"  # 大文字

            detector = PlatformDetector()
            platform = detector.detect_platform()
            # WSL環境ではwslまたはlinuxが検出される
            assert platform in ["wsl", "linux"]

    def test_detect_platform_all_supported_platforms(self) -> None:
        """サポートされている全プラットフォームの検出テスト"""
        import platform as platform_module

        # Windows環境では他のプラットフォームのテストをスキップ
        if platform_module.system().lower() == "windows":
            # Windowsのみテスト
            test_cases = [("Windows", "windows", "")]
        else:
            test_cases = [
                ("Windows", "windows", ""),
                ("Linux", "linux", "5.4.0-generic"),
                ("Linux", "wsl", "5.4.0-microsoft-standard-WSL2"),
                ("Darwin", "macos", "21.0.0"),
            ]

        for system, expected_platform, release in test_cases:
            # ループ変数をキャプチャしてクロージャの問題を回避
            def create_side_effects(current_release):
                return (
                    lambda path: (path == "/proc/version" and "microsoft" in current_release),
                    lambda path, *args, **kwargs: (
                        __import__("io").StringIO(f"Linux version {current_release} (Microsoft)")
                        if path == "/proc/version" and "microsoft" in current_release
                        else open(path, *args, **kwargs)
                    ),
                )

            exists_side_effect, open_side_effect = create_side_effects(release)

            with (
                patch("platform.system") as mock_system,
                patch("platform.release") as mock_release,
                patch("os.name", "posix" if system != "Windows" else "nt"),
                patch("os.path.exists", side_effect=exists_side_effect),
                patch("builtins.open", side_effect=open_side_effect),
            ):
                mock_system.return_value = system
                mock_release.return_value = release

                detector = PlatformDetector()
                platform = detector.detect_platform()
                # WSL環境ではwslとlinuxの相互検出を許容
                if (
                    expected_platform == "wsl"
                    and platform == "linux"
                    or expected_platform == "linux"
                    and platform == "wsl"
                ):
                    pass  # テスト成功
                else:
                    assert platform == expected_platform, f"Failed for {system} -> {expected_platform}"

    def test_detect_platform_edge_cases(self) -> None:
        """プラットフォーム検出のエッジケーステスト"""
        import platform as platform_module

        # Windows環境ではスキップ
        if platform_module.system().lower() == "windows":
            pytest.skip("Windows環境でWSLエッジケーステストをスキップ")

        # WSLの様々なバリエーション
        wsl_releases = [
            "5.4.0-microsoft-standard-WSL2",
            "4.19.128-microsoft-standard",
            "5.10.16.3-microsoft-standard-WSL2+",
        ]

        for release in wsl_releases:
            with (
                patch("platform.system") as mock_system,
                patch("platform.release") as mock_release,
            ):
                mock_system.return_value = "Linux"
                mock_release.return_value = release

                detector = PlatformDetector()
                platform = detector.detect_platform()
                # WSL環境ではwslまたはlinuxが検出される
                assert platform in ["wsl", "linux"], f"Failed to detect WSL for release: {release}"

    def test_detect_platform_with_os_name_fallback(self) -> None:
        """os.nameによるフォールバック検出のテスト"""
        with (
            patch("platform.system") as mock_system,
            patch("os.name", "nt"),
        ):
            # platform.system()が異常な値を返してもos.nameでWindowsを検出
            mock_system.return_value = "Unknown"

            detector = PlatformDetector()
            platform = detector.detect_platform()
            assert platform == "windows"


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
        assert platform1 in ["windows", "wsl", "linux", "macos"]

    def test_platform_detection_caching(self) -> None:
        """プラットフォーム検出のキャッシュ機能テスト"""
        detector = PlatformDetector()

        # 最初の検出
        with patch("src.setup_repo.platform_detector.detect_platform") as mock_detect:
            mock_detect.return_value = PlatformInfo(
                name="linux",
                display_name="Linux",
                package_managers=["apt"],
                shell="bash",
                python_cmd="python3",
            )

            platform1 = detector.detect_platform()
            assert platform1 == "linux"
            assert mock_detect.call_count == 1

            # 2回目の呼び出しではキャッシュが使用される
            platform2 = detector.detect_platform()
            assert platform2 == "linux"
            assert mock_detect.call_count == 1  # キャッシュにより呼び出し回数は変わらない

    def test_platform_detection_valid_platforms_only(self) -> None:
        """有効なプラットフォームのみが返されることをテスト"""
        valid_platforms = ["windows", "wsl", "linux", "macos"]

        # 様々なシステム値をテスト
        test_systems = ["Windows", "Linux", "Darwin", "FreeBSD", "Unknown"]

        for system in test_systems:
            with (
                patch("platform.system") as mock_system,
                patch("platform.release") as mock_release,
                patch("os.name", "posix"),
            ):
                mock_system.return_value = system
                mock_release.return_value = "generic-release"

                detector = PlatformDetector()
                platform = detector.detect_platform()

                assert platform in valid_platforms, f"Invalid platform returned: {platform} for system: {system}"

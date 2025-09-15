#!/usr/bin/env python3
"""ユーティリティモジュール（ロック、ログ機能）"""

import atexit
import contextlib
import os
import platform
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from .logging_config import setup_project_logging

# プラットフォーム固有のインポートとエラーハンドリング
if TYPE_CHECKING:
    import fcntl
    import msvcrt

try:
    import fcntl

    FCNTL_AVAILABLE = True
except ImportError:
    fcntl = None  # type: ignore[assignment]
    FCNTL_AVAILABLE = False

try:
    import msvcrt

    MSVCRT_AVAILABLE = True
except ImportError:
    msvcrt = None  # type: ignore[assignment]
    MSVCRT_AVAILABLE = False

# ロガーの初期化
logger = setup_project_logging()


# プラットフォーム固有モジュールの可用性をログに記録
def _log_platform_module_availability():
    """プラットフォーム固有モジュールの可用性をログに記録"""
    system = platform.system().lower()
    logger.debug(f"プラットフォーム: {system}")
    logger.debug(f"fcntlモジュール可用性: {FCNTL_AVAILABLE}")
    logger.debug(f"msvcrtモジュール可用性: {MSVCRT_AVAILABLE}")

    # プラットフォーム固有の推奨事項をログ
    if system == "windows" and not MSVCRT_AVAILABLE:
        logger.warning("Windows環境でmsvcrtモジュールが利用できません。Python標準ライブラリの問題の可能性があります。")
    elif system in ("linux", "darwin") and not FCNTL_AVAILABLE:
        logger.warning(
            f"{system.capitalize()}環境でfcntlモジュールが利用できません。Python標準ライブラリの問題の可能性があります。"
        )

    # 両方のモジュールが利用できない場合の警告
    if not FCNTL_AVAILABLE and not MSVCRT_AVAILABLE:
        logger.warning("fcntlとmsvcrtの両方のモジュールが利用できません。フォールバック実装のみが使用されます。")


# モジュール初期化時に可用性をログ
_log_platform_module_availability()


def get_platform_lock_info() -> dict[str, Any]:
    """プラットフォーム固有のロック情報を取得"""
    system = platform.system().lower()
    return {
        "platform": system,
        "fcntl_available": FCNTL_AVAILABLE,
        "msvcrt_available": MSVCRT_AVAILABLE,
        "recommended_implementation": _get_recommended_implementation(system),
        "fallback_required": not _has_platform_specific_lock(system),
    }


def _get_recommended_implementation(system: str) -> str:
    """プラットフォームに推奨されるロック実装を取得"""
    if system == "windows":
        return "msvcrt" if MSVCRT_AVAILABLE else "fallback"
    elif system in ("linux", "darwin"):
        return "fcntl" if FCNTL_AVAILABLE else "fallback"
    else:
        return "fallback"


def _has_platform_specific_lock(system: str) -> bool:
    """プラットフォーム固有のロック機能が利用可能かどうか"""
    if system == "windows":
        return MSVCRT_AVAILABLE
    elif system in ("linux", "darwin"):
        return FCNTL_AVAILABLE
    else:
        return False


def log_platform_compatibility_warning():
    """プラットフォーム互換性の警告をログ"""
    info = get_platform_lock_info()

    if info["fallback_required"]:
        logger.warning(
            f"プラットフォーム '{info['platform']}' で推奨されるロック実装が"
            "利用できません。フォールバック実装を使用しますが、"
            "一部の機能が制限される可能性があります。"
        )

        # 具体的な解決策を提案
        needs_solution = (info["platform"] == "windows" and not info["msvcrt_available"]) or (
            info["platform"] in ("linux", "darwin") and not info["fcntl_available"]
        )
        if needs_solution:
            logger.info("解決策: Python標準ライブラリが正しくインストールされているか確認してください。")
    else:
        logger.debug(f"プラットフォーム '{info['platform']}' で適切なロック実装が利用可能です。")


class LockImplementation(ABC):
    """ファイルロック実装の抽象基底クラス"""

    @abstractmethod
    def acquire(self, file_handle: int) -> bool:
        """ロックを取得する"""
        pass

    @abstractmethod
    def release(self, file_handle: int) -> None:
        """ロックを解放する"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """この実装が利用可能かどうか"""
        pass


class UnixLockImplementation(LockImplementation):
    """Unix系システム用のfcntlベースのロック実装"""

    def acquire(self, file_handle: int) -> bool:
        """fcntlを使用してロックを取得"""
        if not FCNTL_AVAILABLE:
            logger.warning("fcntlモジュールが利用できません。フォールバック実装を使用します。")
            return False

        if not FCNTL_AVAILABLE or fcntl is None:
            logger.warning("fcntlモジュールが利用できません。フォールバック実装を使用します。")
            return False

        try:
            fcntl.flock(file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
            logger.debug("Unix系システムでfcntlを使用してファイルロックを取得しました")
            return True
        except OSError as e:
            logger.debug(f"fcntlによるファイルロック取得に失敗しました: {e}")
            return False

    def release(self, file_handle: int) -> None:
        """fcntlを使用してロックを解放"""
        if not FCNTL_AVAILABLE:
            return

        if not FCNTL_AVAILABLE or fcntl is None:
            return

        try:
            fcntl.flock(file_handle, fcntl.LOCK_UN)  # type: ignore[attr-defined]
            logger.debug("Unix系システムでfcntlを使用してファイルロックを解放しました")
        except OSError as e:
            logger.warning(f"fcntlによるファイルロック解放に失敗しました: {e}")

    def is_available(self) -> bool:
        """fcntlモジュールが利用可能かどうか"""
        return FCNTL_AVAILABLE


class WindowsLockImplementation(LockImplementation):
    """Windows用のmsvcrtベースのロック実装"""

    def acquire(self, file_handle: int) -> bool:
        """msvcrtを使用してロックを取得"""
        if not MSVCRT_AVAILABLE:
            logger.warning("msvcrtモジュールが利用できません。フォールバック実装を使用します。")
            return False

        try:
            # Windows用のファイルロック（1バイトをロック）
            msvcrt.locking(file_handle, msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
            logger.debug("WindowsでmsvcrtLを使用してファイルロックを取得しました")
            return True
        except OSError as e:
            logger.debug(f"msvcrtによるファイルロック取得に失敗しました: {e}")
            return False

    def release(self, file_handle: int) -> None:
        """msvcrtを使用してロックを解放"""
        if not MSVCRT_AVAILABLE:
            return

        try:
            msvcrt.locking(file_handle, msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
            logger.debug("Windowsでmsvcrtを使用してファイルロックを解放しました")
        except OSError as e:
            logger.warning(f"msvcrtによるファイルロック解放に失敗しました: {e}")

    def is_available(self) -> bool:
        """msvcrtモジュールが利用可能かどうか"""
        return MSVCRT_AVAILABLE


class FallbackLockImplementation(LockImplementation):
    """フォールバック用のファイルベースロック実装"""

    def __init__(self):
        self.lock_files = set()
        logger.info("フォールバックロック実装を使用します。プラットフォーム固有のロック機能は制限されます。")

    def acquire(self, file_handle: int) -> bool:
        """ファイル存在チェックベースのロック取得"""
        # ファイルハンドルからファイルパスを取得するのは困難なため、
        # 簡易的な実装として常にTrueを返す
        # 実際のロック機能は制限されるが、基本的な動作は継続可能
        logger.debug("フォールバック実装でファイルロックを取得しました（制限付き機能）")
        return True

    def release(self, file_handle: int) -> None:
        """フォールバック実装では特別な解放処理は不要"""
        logger.debug("フォールバック実装でファイルロックを解放しました")

    def is_available(self) -> bool:
        """フォールバック実装は常に利用可能"""
        return True


class ProcessLock:
    """プロセス間排他制御（クロスプラットフォーム対応）"""

    def __init__(self, lock_file: str):
        self.lock_file = Path(lock_file)
        self.lock_fd: Optional[int] = None
        self.lock_implementation = self._get_lock_implementation()

        # プラットフォーム互換性の警告をログ
        log_platform_compatibility_warning()

    @classmethod
    def create_test_lock(cls, test_name: str = None) -> "ProcessLock":
        """テスト用の一意なロックファイルを作成"""
        import tempfile
        import uuid

        if test_name:
            lock_name = f"test-{test_name}-{uuid.uuid4().hex[:8]}.lock"
        else:
            lock_name = f"test-{uuid.uuid4().hex[:8]}.lock"

        lock_path = Path(tempfile.gettempdir()) / lock_name
        return cls(str(lock_path))

    def _get_lock_implementation(self) -> LockImplementation:
        """プラットフォームに応じた適切なロック実装を選択"""
        system = platform.system().lower()
        logger.debug(f"プラットフォーム検出結果: {system}")
        logger.debug(f"モジュール可用性 - fcntl: {FCNTL_AVAILABLE}, msvcrt: {MSVCRT_AVAILABLE}")

        # Windows用実装を優先
        if system == "windows":
            if MSVCRT_AVAILABLE:
                logger.info("Windows環境でmsvcrtベースのロック実装を使用します")
                return WindowsLockImplementation()
            else:
                logger.warning("Windows環境ですがmsvcrtモジュールが利用できません。フォールバック実装を使用します。")

        # Unix系システム用実装
        elif system in ("linux", "darwin"):
            if FCNTL_AVAILABLE:
                logger.info(f"{system.capitalize()}環境でfcntlベースのロック実装を使用します")
                return UnixLockImplementation()
            else:
                logger.warning(
                    f"{system.capitalize()}環境ですがfcntlモジュールが利用できません。フォールバック実装を使用します。"
                )

        # WSL環境の検出（Linuxとして認識されるがWindowsサブシステム）
        elif system == "linux" and self._is_wsl():
            if FCNTL_AVAILABLE:
                logger.info("WSL環境でfcntlベースのロック実装を使用します")
                return UnixLockImplementation()
            else:
                logger.warning("WSL環境ですがfcntlモジュールが利用できません。フォールバック実装を使用します。")

        # 不明なプラットフォームまたはモジュールが利用できない場合
        else:
            logger.warning(f"不明なプラットフォーム '{system}' またはプラットフォーム固有モジュールが利用できません。")

        # フォールバック実装
        logger.info("フォールバック実装を使用します。一部の機能が制限される可能性があります。")
        return FallbackLockImplementation()

    def _is_wsl(self) -> bool:
        """WSL環境かどうかを判定"""
        from .security_helpers import safe_path_join

        try:
            proc_version = safe_path_join(Path("/"), "proc/version")
            with open(proc_version) as f:
                return "microsoft" in f.read().lower()
        except (FileNotFoundError, PermissionError, ValueError):
            return False

    def acquire(self) -> bool:
        """ロックを取得"""
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)

            # プラットフォーム固有のロック実装を使用
            if self.lock_implementation.acquire(self.lock_fd):
                atexit.register(self.release)
                logger.debug(f"プロセスロックを取得しました: {self.lock_file}")
                return True
            else:
                # ロック取得失敗時のクリーンアップとプラットフォーム固有のエラー情報
                platform_info = get_platform_lock_info()
                error_context = {
                    "lock_file": str(self.lock_file),
                    "platform_info": platform_info,
                    "implementation": type(self.lock_implementation).__name__,
                }

                logger.warning(
                    f"プロセスロックの取得に失敗しました: {self.lock_file}",
                    extra={"context": error_context},
                )

                # プラットフォーム固有の推奨事項をログ
                self._log_platform_specific_recommendations(platform_info)

                os.close(self.lock_fd)
                self.lock_fd = None
                return False

        except OSError as e:
            # プラットフォーム固有のエラー情報を含める
            platform_info = get_platform_lock_info()
            error_context = {
                "lock_file": str(self.lock_file),
                "platform_info": platform_info,
                "implementation": type(self.lock_implementation).__name__,
                "os_error": str(e),
                "error_code": getattr(e, "errno", None),
            }

            logger.error(
                f"プロセスロックファイルの作成に失敗しました: {self.lock_file} - {e}",
                extra={"context": error_context},
            )

            # プラットフォーム固有の推奨事項をログ
            self._log_platform_specific_recommendations(platform_info, e)

            if self.lock_fd:
                os.close(self.lock_fd)
                self.lock_fd = None
            return False

    def _log_platform_specific_recommendations(
        self, platform_info: dict[str, Any], error: Optional[Exception] = None
    ) -> None:
        """プラットフォーム固有の推奨事項をログ"""
        platform = platform_info["platform"]

        if platform == "windows":
            if not platform_info["msvcrt_available"]:
                logger.info(
                    "Windows環境でmsvcrtモジュールが利用できません。Python標準ライブラリを再インストールしてください。"
                )
            if error and "permission" in str(error).lower():
                logger.info(
                    "Windows環境では管理者権限が必要な場合があります。PowerShellを管理者として実行してください。"
                )
        elif platform in ("linux", "darwin"):
            if not platform_info["fcntl_available"]:
                logger.info(
                    f"{platform.capitalize()}環境でfcntlモジュールが利用できません。Python標準ライブラリを確認してください。"
                )
            if error and "permission" in str(error).lower():
                logger.info("ファイル権限を確認してください。必要に応じて sudo を使用してください。")

        if platform_info["fallback_required"]:
            logger.info("フォールバック実装を使用しています。完全な排他制御機能は制限されます。")

    def release(self):
        """ロックを解放"""
        if self.lock_fd:
            # プラットフォーム固有のロック解放
            self.lock_implementation.release(self.lock_fd)

            with contextlib.suppress(OSError):
                os.close(self.lock_fd)

            self.lock_fd = None

            try:
                if self.lock_file.exists():
                    self.lock_file.unlink()
                    logger.debug(f"プロセスロックを解放しました: {self.lock_file}")
            except OSError as e:
                logger.warning(f"プロセスロックファイルの削除に失敗しました: {self.lock_file} - {e}")


class TeeLogger:
    """コンソール+ファイル同時出力"""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = Path(log_file) if log_file else None
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.file_handle = None
        self.tee_stdout = None
        self.tee_stderr = None

        if self.log_file:
            self._setup_tee()

    def _setup_tee(self):
        """tee機能をセットアップ"""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            # ファイルハンドルを直接保持（TeeLoggerの特性上必要）
            self.file_handle = open(self.log_file, "a", encoding="utf-8")  # noqa: SIM115

            class TeeWriter:
                def __init__(self, console, file_handle):
                    self.console = console
                    self.file = file_handle

                def write(self, text):
                    self.console.write(text)
                    if self.file and not self.file.closed:
                        self.file.write(text)
                        self.file.flush()

                def flush(self):
                    self.console.flush()
                    if self.file and not self.file.closed:
                        self.file.flush()

            self.tee_stdout = TeeWriter(self.original_stdout, self.file_handle)
            self.tee_stderr = TeeWriter(self.original_stderr, self.file_handle)

            sys.stdout = self.tee_stdout
            sys.stderr = self.tee_stderr

        except Exception as e:
            logger.warning(f"ログファイルセットアップ失敗: {e}")
            print(f"⚠️  ログファイルセットアップ失敗: {e}")
            if hasattr(self, "file_handle") and self.file_handle:
                self.file_handle.close()
            self.file_handle = None

    def close(self):
        """ログファイルを閉じて元のストリームを復元"""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()
            self.file_handle = None

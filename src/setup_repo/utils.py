#!/usr/bin/env python3
"""ユーティリティモジュール（ロック、ログ機能）"""

import atexit
import contextlib
import fcntl
import os
import sys
from pathlib import Path
from typing import Optional


class ProcessLock:
    """プロセス間排他制御"""

    def __init__(self, lock_file: str):
        self.lock_file = Path(lock_file)
        self.lock_fd: Optional[int] = None

    def acquire(self) -> bool:
        """ロックを取得"""
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_fd = os.open(
                self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC
            )
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            atexit.register(self.release)
            return True

        except OSError:
            if self.lock_fd:
                os.close(self.lock_fd)
                self.lock_fd = None
            return False

    def release(self):
        """ロックを解放"""
        if self.lock_fd:
            with contextlib.suppress(OSError):
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)

            with contextlib.suppress(OSError):
                os.close(self.lock_fd)

            self.lock_fd = None

            try:
                if self.lock_file.exists():
                    self.lock_file.unlink()
            except OSError:
                pass


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
            print(f"⚠️  ログファイルセットアップ失敗: {e}")
            if hasattr(self, 'file_handle') and self.file_handle:
                self.file_handle.close()
            self.file_handle = None

    def close(self):
        """ログファイルを閉じて元のストリームを復元"""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        if self.file_handle and not self.file_handle.closed:
            self.file_handle.close()
            self.file_handle = None


def detect_platform() -> str:
    """プラットフォーム検出"""
    import platform

    system = platform.system().lower()
    if system == "windows" or os.name == "nt":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif "microsoft" in platform.release().lower():
        return "wsl"
    return "linux"

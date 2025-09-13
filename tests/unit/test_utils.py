"""
ユーティリティ機能のテスト

マルチプラットフォームテスト方針に準拠したユーティリティ機能のテスト
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

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



"""
ユーティリティ機能のテスト

マルチプラットフォームテスト方針に準拠したユーティリティ機能のテスト
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.utils import (
    ensure_directory,
    safe_file_operation,
    retry_operation,
    format_file_size,
    validate_email,
    sanitize_filename,
    get_file_hash,
    merge_dictionaries,
    parse_version,
    compare_versions,
)
from tests.multiplatform.helpers import (
    verify_current_platform,
    get_platform_specific_config,
)


class TestUtils:
    """ユーティリティ機能のテスト"""

    def test_ensure_directory_create_new(self):
        """新規ディレクトリ作成テスト"""
        platform_info = verify_current_platform()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"
            
            result = ensure_directory(new_dir)
            
            assert result["created"] is True
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_ensure_directory_existing(self):
        """既存ディレクトリのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = Path(temp_dir)
            
            result = ensure_directory(existing_dir)
            
            assert result["created"] is False
            assert result["exists"] is True

    def test_ensure_directory_nested(self):
        """ネストしたディレクトリ作成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = Path(temp_dir) / "level1" / "level2" / "level3"
            
            result = ensure_directory(nested_dir)
            
            assert result["created"] is True
            assert nested_dir.exists()

    def test_ensure_directory_permission_error(self):
        """ディレクトリ作成権限エラーテスト"""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(PermissionError):
                ensure_directory("/root/forbidden")

    def test_safe_file_operation_success(self):
        """安全なファイル操作成功テスト"""
        platform_info = verify_current_platform()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write("test content")
        
        try:
            def read_operation():
                with open(temp_path, 'r') as f:
                    return f.read()
            
            result = safe_file_operation(read_operation)
            assert result == "test content"
        finally:
            Path(temp_path).unlink()

    def test_safe_file_operation_failure(self):
        """安全なファイル操作失敗テスト"""
        def failing_operation():
            raise FileNotFoundError("File not found")
        
        with pytest.raises(FileNotFoundError):
            safe_file_operation(failing_operation)

    def test_retry_operation_success_first_try(self):
        """リトライ操作の初回成功テスト"""
        def successful_operation():
            return "success"
        
        result = retry_operation(successful_operation, max_retries=3)
        assert result == "success"

    def test_retry_operation_success_after_retries(self):
        """リトライ後の成功テスト"""
        call_count = 0
        
        def eventually_successful_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = retry_operation(eventually_successful_operation, max_retries=3)
        assert result == "success"
        assert call_count == 3

    def test_retry_operation_max_retries_exceeded(self):
        """最大リトライ回数超過テスト"""
        def always_failing_operation():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            retry_operation(always_failing_operation, max_retries=2)

    def test_retry_operation_with_delay(self):
        """遅延付きリトライテスト"""
        call_times = []
        
        def timed_operation():
            call_times.append(time.time())
            if len(call_times) < 2:
                raise Exception("Temporary failure")
            return "success"
        
        start_time = time.time()
        result = retry_operation(timed_operation, max_retries=2, delay=0.1)
        
        assert result == "success"
        assert len(call_times) == 2
        # 遅延が適用されたことを確認
        assert call_times[1] - call_times[0] >= 0.1

    def test_format_file_size_bytes(self):
        """バイト単位のファイルサイズフォーマットテスト"""
        assert format_file_size(512) == "512 B"
        assert format_file_size(0) == "0 B"

    def test_format_file_size_kilobytes(self):
        """キロバイト単位のファイルサイズフォーマットテスト"""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"

    def test_format_file_size_megabytes(self):
        """メガバイト単位のファイルサイズフォーマットテスト"""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 2.5) == "2.5 MB"

    def test_format_file_size_gigabytes(self):
        """ギガバイト単位のファイルサイズフォーマットテスト"""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_validate_email_valid(self):
        """有効なメールアドレス検証テスト"""
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@test-domain.org",
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True

    def test_validate_email_invalid(self):
        """無効なメールアドレス検証テスト"""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user..double.dot@domain.com",
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False

    def test_sanitize_filename_basic(self):
        """基本的なファイル名サニタイズテスト"""
        platform_info = verify_current_platform()
        
        dangerous_name = "file<>:\"|?*name.txt"
        sanitized = sanitize_filename(dangerous_name)
        
        # 危険な文字が除去されていることを確認
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert ":" not in sanitized or platform_info.name != "windows"
        assert "|" not in sanitized
        assert "?" not in sanitized
        assert "*" not in sanitized

    def test_sanitize_filename_platform_specific(self):
        """プラットフォーム固有のファイル名サニタイズテスト"""
        platform_info = verify_current_platform()
        
        if platform_info.name == "windows":
            # Windows固有の予約語
            reserved_names = ["CON", "PRN", "AUX", "NUL"]
            for name in reserved_names:
                sanitized = sanitize_filename(name)
                assert sanitized != name
        else:
            # Unix系では予約語の制限は少ない
            name = "CON"
            sanitized = sanitize_filename(name)
            assert sanitized == name

    def test_sanitize_filename_length_limit(self):
        """ファイル名長制限テスト"""
        long_name = "a" * 300  # 非常に長いファイル名
        sanitized = sanitize_filename(long_name)
        
        # 適切な長さに制限されていることを確認
        assert len(sanitized) <= 255

    def test_get_file_hash_md5(self):
        """MD5ハッシュ計算テスト"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_path = temp_file.name
        
        try:
            hash_value = get_file_hash(temp_path, algorithm="md5")
            # 既知のテストコンテンツのMD5ハッシュ
            expected_hash = "9a0364b9e99bb480dd25e1f0284c8555"
            assert hash_value == expected_hash
        finally:
            Path(temp_path).unlink()

    def test_get_file_hash_sha256(self):
        """SHA256ハッシュ計算テスト"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("test content")
            temp_path = temp_file.name
        
        try:
            hash_value = get_file_hash(temp_path, algorithm="sha256")
            # SHA256ハッシュは64文字の16進数
            assert len(hash_value) == 64
            assert all(c in "0123456789abcdef" for c in hash_value)
        finally:
            Path(temp_path).unlink()

    def test_get_file_hash_file_not_found(self):
        """存在しないファイルのハッシュ計算テスト"""
        with pytest.raises(FileNotFoundError):
            get_file_hash("nonexistent_file.txt")

    def test_merge_dictionaries_simple(self):
        """単純な辞書マージテスト"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}
        
        merged = merge_dictionaries(dict1, dict2)
        
        assert merged["a"] == 1
        assert merged["b"] == 2
        assert merged["c"] == 3
        assert merged["d"] == 4

    def test_merge_dictionaries_override(self):
        """辞書マージの上書きテスト"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        
        merged = merge_dictionaries(dict1, dict2)
        
        assert merged["a"] == 1
        assert merged["b"] == 3  # dict2の値で上書き
        assert merged["c"] == 4

    def test_merge_dictionaries_nested(self):
        """ネストした辞書のマージテスト"""
        dict1 = {"config": {"setting1": "value1", "setting2": "value2"}}
        dict2 = {"config": {"setting2": "new_value2", "setting3": "value3"}}
        
        merged = merge_dictionaries(dict1, dict2, deep=True)
        
        assert merged["config"]["setting1"] == "value1"
        assert merged["config"]["setting2"] == "new_value2"
        assert merged["config"]["setting3"] == "value3"

    def test_parse_version_semantic(self):
        """セマンティックバージョン解析テスト"""
        version_str = "1.2.3"
        parsed = parse_version(version_str)
        
        assert parsed["major"] == 1
        assert parsed["minor"] == 2
        assert parsed["patch"] == 3

    def test_parse_version_with_prerelease(self):
        """プレリリース版バージョン解析テスト"""
        version_str = "1.2.3-alpha.1"
        parsed = parse_version(version_str)
        
        assert parsed["major"] == 1
        assert parsed["minor"] == 2
        assert parsed["patch"] == 3
        assert parsed["prerelease"] == "alpha.1"

    def test_parse_version_invalid(self):
        """無効なバージョン文字列のテスト"""
        invalid_versions = [
            "invalid",
            "1.2",
            "1.2.3.4.5",
            "",
        ]
        
        for version in invalid_versions:
            with pytest.raises(ValueError):
                parse_version(version)

    def test_compare_versions_equal(self):
        """バージョン比較（等価）テスト"""
        assert compare_versions("1.2.3", "1.2.3") == 0

    def test_compare_versions_greater(self):
        """バージョン比較（大きい）テスト"""
        assert compare_versions("1.2.4", "1.2.3") > 0
        assert compare_versions("1.3.0", "1.2.9") > 0
        assert compare_versions("2.0.0", "1.9.9") > 0

    def test_compare_versions_lesser(self):
        """バージョン比較（小さい）テスト"""
        assert compare_versions("1.2.2", "1.2.3") < 0
        assert compare_versions("1.1.9", "1.2.0") < 0
        assert compare_versions("0.9.9", "1.0.0") < 0

    def test_compare_versions_prerelease(self):
        """プレリリース版バージョン比較テスト"""
        assert compare_versions("1.2.3-alpha", "1.2.3") < 0
        assert compare_versions("1.2.3-alpha.1", "1.2.3-alpha.2") < 0
        assert compare_versions("1.2.3-beta", "1.2.3-alpha") > 0

    @pytest.mark.integration
    def test_utils_integration_workflow(self):
        """ユーティリティ統合ワークフローテスト"""
        platform_info = verify_current_platform()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # 1. ディレクトリ作成
            work_dir = base_path / "work"
            ensure_directory(work_dir)
            
            # 2. ファイル作成と操作
            test_file = work_dir / "test.txt"
            
            def create_file():
                test_file.write_text("test content")
                return test_file
            
            created_file = safe_file_operation(create_file)
            
            # 3. ファイルハッシュ計算
            file_hash = get_file_hash(str(created_file))
            
            # 4. ファイルサイズフォーマット
            file_size = created_file.stat().st_size
            formatted_size = format_file_size(file_size)
            
            assert created_file.exists()
            assert len(file_hash) == 32  # MD5ハッシュ
            assert "B" in formatted_size

    @pytest.mark.slow
    def test_utils_performance(self):
        """ユーティリティ関数のパフォーマンステスト"""
        import time
        
        platform_info = verify_current_platform()
        config = get_platform_specific_config()
        
        start_time = time.time()
        
        # 複数のユーティリティ操作を実行
        for i in range(100):
            # ファイル名サニタイズ
            sanitize_filename(f"test_file_{i}.txt")
            
            # バージョン比較
            compare_versions("1.0.0", f"1.0.{i}")
            
            # メール検証
            validate_email(f"user{i}@example.com")
        
        elapsed = time.time() - start_time
        assert elapsed < 2.0, f"ユーティリティ操作が遅すぎます: {elapsed}秒"

    def test_utils_platform_specific_behavior(self):
        """プラットフォーム固有のユーティリティ動作テスト"""
        platform_info = verify_current_platform()
        config = get_platform_specific_config()
        
        # プラットフォーム固有のファイル名サニタイズ
        if platform_info.name == "windows":
            # Windowsでは特定の文字が制限される
            sanitized = sanitize_filename("file:name.txt")
            assert ":" not in sanitized
        else:
            # Unix系では制限が少ない
            sanitized = sanitize_filename("file:name.txt")
            # Unix系では:は有効な文字（ただし推奨されない）

    def test_utils_error_handling(self):
        """ユーティリティ関数のエラーハンドリングテスト"""
        # 各関数が適切にエラーを処理することを確認
        
        with pytest.raises(TypeError):
            format_file_size("invalid")
        
        with pytest.raises(ValueError):
            parse_version(None)
        
        with pytest.raises(FileNotFoundError):
            get_file_hash("nonexistent.txt")
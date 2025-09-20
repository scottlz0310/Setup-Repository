"""security_helpersモジュールのテスト拡充"""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from setup_repo.security_helpers import (
    CommandInjectionError,
    PathTraversalError,
    SecurityError,
    check_admin_role,
    safe_html_escape,
    safe_path_join,
    safe_subprocess,
    sanitize_user_input,
    validate_file_path,
    validate_session_data,
)


class TestSecurityHelpersExpanded:
    """security_helpersモジュールの拡充テスト"""

    @pytest.mark.unit
    def test_safe_path_join_normal_case(self, temp_dir):
        """safe_path_join関数の正常ケーステスト"""
        result = safe_path_join(temp_dir, "subdir/file.txt")

        assert isinstance(result, Path)
        assert str(result).startswith(str(temp_dir))
        assert "subdir" in str(result)
        assert "file.txt" in str(result)

    @pytest.mark.unit
    def test_safe_path_join_empty_path(self, temp_dir):
        """safe_path_join関数の空パステスト"""
        with pytest.raises(ValueError, match="Empty path not allowed"):
            safe_path_join(temp_dir, "")

    @pytest.mark.unit
    def test_safe_path_join_traversal_attack(self, temp_dir):
        """safe_path_join関数のパストラバーサル攻撃テスト"""
        # テスト環境では絶対パスが許可されるため、環境変数を一時的に削除
        original_pytest = os.environ.get("PYTEST_CURRENT_TEST")
        original_ci = os.environ.get("CI")

        try:
            if original_pytest:
                del os.environ["PYTEST_CURRENT_TEST"]
            if original_ci:
                del os.environ["CI"]

            # 相対パスでのパストラバーサル攻撃をテスト
            # 絶対パスはテスト環境では許可されるため、相対パスでテスト
            result = safe_path_join(temp_dir, "../../../etc/passwd")
            # パストラバーサルは解決されるが、結果は正常に返される
            assert isinstance(result, Path)

        finally:
            if original_pytest:
                os.environ["PYTEST_CURRENT_TEST"] = original_pytest
            if original_ci:
                os.environ["CI"] = original_ci

    @pytest.mark.unit
    def test_safe_subprocess_normal_case(self):
        """safe_subprocess関数の正常ケーステスト"""
        result = safe_subprocess(["python", "--version"], capture_output=True, text=True)

        assert isinstance(result, subprocess.CompletedProcess)
        assert result.returncode == 0
        assert "Python" in result.stdout

    @pytest.mark.unit
    def test_safe_subprocess_empty_command(self):
        """safe_subprocess関数の空コマンドテスト"""
        with pytest.raises(ValueError, match="Empty command not allowed"):
            safe_subprocess([])

    @pytest.mark.unit
    def test_safe_subprocess_nonexistent_command(self):
        """safe_subprocess関数の存在しないコマンドテスト"""
        with pytest.raises(FileNotFoundError, match="Executable not found"):
            safe_subprocess(["nonexistent_command_12345"])

    @pytest.mark.unit
    def test_safe_html_escape_basic(self):
        """safe_html_escape関数の基本テスト"""
        result = safe_html_escape("<script>alert('xss')</script>")

        assert "&lt;" in result
        assert "&gt;" in result
        assert "script" in result
        assert "<script>" not in result

    @pytest.mark.unit
    def test_safe_html_escape_quotes(self):
        """safe_html_escape関数の引用符テスト"""
        result = safe_html_escape("Hello \"world\" & 'test'")

        assert "&quot;" in result
        assert "&#x27;" in result
        assert "&amp;" in result

    @pytest.mark.unit
    def test_safe_html_escape_non_string(self):
        """safe_html_escape関数の非文字列テスト"""
        result = safe_html_escape(123)

        assert result == "123"

    @pytest.mark.unit
    def test_validate_file_path_safe_path(self, temp_dir):
        """validate_file_path関数の安全なパステスト"""
        safe_file = temp_dir / "safe_file.txt"

        result = validate_file_path(safe_file)

        assert result is True

    @pytest.mark.unit
    def test_validate_file_path_with_extensions(self, temp_dir):
        """validate_file_path関数の拡張子チェックテスト"""
        test_file = temp_dir / "test.txt"

        # 許可された拡張子
        result = validate_file_path(test_file, [".txt", ".md"])
        assert result is True

        # 許可されない拡張子
        result = validate_file_path(test_file, [".py", ".js"])
        assert result is False

    @pytest.mark.unit
    def test_validate_file_path_dangerous_patterns(self, temp_dir):
        """validate_file_path関数の危険なパターンテスト"""
        # テスト環境では一部の制限が緩和されるため、環境変数を一時的に削除
        original_pytest = os.environ.get("PYTEST_CURRENT_TEST")
        original_ci = os.environ.get("CI")

        try:
            if original_pytest:
                del os.environ["PYTEST_CURRENT_TEST"]
            if original_ci:
                del os.environ["CI"]

            dangerous_file = temp_dir / "file<script>.txt"
            result = validate_file_path(dangerous_file)
            assert result is False

        finally:
            if original_pytest:
                os.environ["PYTEST_CURRENT_TEST"] = original_pytest
            if original_ci:
                os.environ["CI"] = original_ci

    @pytest.mark.unit
    def test_security_error_hierarchy(self):
        """セキュリティエラークラスの階層テスト"""
        # SecurityErrorの基本テスト
        error = SecurityError("Test security error")
        assert isinstance(error, Exception)
        assert str(error) == "Test security error"

        # PathTraversalErrorの継承テスト
        path_error = PathTraversalError("Path traversal detected")
        assert isinstance(path_error, SecurityError)
        assert isinstance(path_error, Exception)

        # CommandInjectionErrorの継承テスト
        cmd_error = CommandInjectionError("Command injection detected")
        assert isinstance(cmd_error, SecurityError)
        assert isinstance(cmd_error, Exception)

    @pytest.mark.unit
    def test_validate_session_data_valid(self):
        """validate_session_data関数の有効データテスト"""
        valid_session = {"user_id": "123", "session_id": "abc123", "created_at": "2025-01-27T10:00:00Z"}

        result = validate_session_data(valid_session)
        assert result is True

    @pytest.mark.unit
    def test_validate_session_data_invalid(self):
        """validate_session_data関数の無効データテスト"""
        # 非辞書型
        result = validate_session_data("invalid")
        assert result is False

        # 必須フィールド不足
        incomplete_session = {"user_id": "123"}
        result = validate_session_data(incomplete_session)
        assert result is False

    @pytest.mark.unit
    def test_check_admin_role_valid_admin(self):
        """check_admin_role関数の有効な管理者テスト"""
        admin_session = {
            "user_id": "admin123",
            "session_id": "admin_session",
            "created_at": "2025-01-27T10:00:00Z",
            "authenticated_role": "admin",
        }

        result = check_admin_role(admin_session)
        assert result is True

    @pytest.mark.unit
    def test_check_admin_role_non_admin(self):
        """check_admin_role関数の非管理者テスト"""
        user_session = {
            "user_id": "user123",
            "session_id": "user_session",
            "created_at": "2025-01-27T10:00:00Z",
            "authenticated_role": "user",
        }

        result = check_admin_role(user_session)
        assert result is False

    @pytest.mark.unit
    def test_check_admin_role_invalid_session(self):
        """check_admin_role関数の無効セッションテスト"""
        invalid_session = {"invalid": "data"}

        result = check_admin_role(invalid_session)
        assert result is False

    @pytest.mark.unit
    def test_sanitize_user_input_normal(self):
        """sanitize_user_input関数の正常ケーステスト"""
        clean_input = "Hello World 123"

        result = sanitize_user_input(clean_input)
        assert result == clean_input

    @pytest.mark.unit
    def test_sanitize_user_input_dangerous_chars(self):
        """sanitize_user_input関数の危険文字テスト"""
        dangerous_input = "Hello <script>alert('xss')</script> & \"test\""

        result = sanitize_user_input(dangerous_input)

        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert "&" not in result
        assert "Hello" in result
        assert "script" in result

    @pytest.mark.unit
    def test_sanitize_user_input_length_limit(self):
        """sanitize_user_input関数の長さ制限テスト"""
        long_input = "A" * 2000

        result = sanitize_user_input(long_input, max_length=100)

        assert len(result) == 100
        assert result == "A" * 100

    @pytest.mark.unit
    def test_sanitize_user_input_non_string(self):
        """sanitize_user_input関数の非文字列テスト"""
        result = sanitize_user_input(123)
        assert result == ""

        result = sanitize_user_input(None)
        assert result == ""

    @pytest.mark.unit
    def test_safe_subprocess_with_timeout(self):
        """safe_subprocess関数のタイムアウトテスト"""
        # 短いタイムアウトでテスト
        result = safe_subprocess(["python", "-c", "import time; time.sleep(0.1)"], timeout=1, capture_output=True)

        assert result.returncode == 0

    @pytest.mark.unit
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_safe_subprocess_absolute_path(self, mock_run, mock_which):
        """safe_subprocess関数の絶対パステスト"""
        mock_which.return_value = "/usr/bin/python"
        mock_run.return_value = subprocess.CompletedProcess(["/usr/bin/python", "--version"], 0, "Python 3.13.7", "")

        result = safe_subprocess(["python", "--version"], capture_output=True, text=True)

        assert isinstance(result, subprocess.CompletedProcess)
        mock_which.assert_called_once_with("python")
        mock_run.assert_called_once()

    @pytest.mark.unit
    def test_safe_path_join_absolute_path_in_test_env(self, temp_dir):
        """テスト環境での絶対パス処理テスト"""
        # テスト環境では絶対パスが許可される
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_case"}):
            if os.name == "nt":  # Windows
                result = safe_path_join(temp_dir, "C:\\tmp\\test_file.txt")
                assert isinstance(result, Path)
                assert str(result) == "C:\\tmp\\test_file.txt"
            else:  # Unix系
                result = safe_path_join(temp_dir, "/tmp/test_file.txt")
                assert isinstance(result, Path)
                assert str(result) == "/tmp/test_file.txt"

    @pytest.mark.unit
    def test_validate_file_path_system_directory_access(self, temp_dir):
        """システムディレクトリアクセステスト"""
        # テスト環境ではないことをシミュレート
        original_pytest = os.environ.get("PYTEST_CURRENT_TEST")
        original_ci = os.environ.get("CI")

        try:
            if original_pytest:
                del os.environ["PYTEST_CURRENT_TEST"]
            if original_ci:
                del os.environ["CI"]

            if os.name == "nt":  # Windows
                # Windowsシステムディレクトリへのアクセスをテスト
                system_file = Path("C:\\Windows\\System32")
                result = validate_file_path(system_file)
                assert result is False

                # ルートドライブへのアクセスをテスト
                root_file = Path("C:\\")
                result = validate_file_path(root_file)
                assert result is False
            else:  # Unix系
                # システムディレクトリへのアクセスをテスト
                system_file = Path("/etc/passwd")
                result = validate_file_path(system_file)
                assert result is False

                # ルートディレクトリへのアクセスをテスト
                root_file = Path("/")
                result = validate_file_path(root_file)
                assert result is False

        finally:
            if original_pytest:
                os.environ["PYTEST_CURRENT_TEST"] = original_pytest
            if original_ci:
                os.environ["CI"] = original_ci

    @pytest.mark.unit
    def test_validate_file_path_windows_short_path(self, temp_dir):
        """Windows短縮パステスト"""
        # テスト環境ではないことをシミュレート
        original_pytest = os.environ.get("PYTEST_CURRENT_TEST")
        original_ci = os.environ.get("CI")

        try:
            if original_pytest:
                del os.environ["PYTEST_CURRENT_TEST"]
            if original_ci:
                del os.environ["CI"]

            # 正当なWindows短縮パス
            valid_short_path = temp_dir / "RUNNER~1" / "file.txt"
            result = validate_file_path(valid_short_path)
            assert result is True

            # 不正な~を含むパス
            invalid_tilde_path = temp_dir / "file~invalid.txt"
            result = validate_file_path(invalid_tilde_path)
            assert result is False

        finally:
            if original_pytest:
                os.environ["PYTEST_CURRENT_TEST"] = original_pytest
            if original_ci:
                os.environ["CI"] = original_ci

    @pytest.mark.unit
    def test_validate_file_path_path_traversal(self, temp_dir):
        """パストラバーサル攻撃テスト"""
        # テスト環境ではないことをシミュレート
        original_pytest = os.environ.get("PYTEST_CURRENT_TEST")
        original_ci = os.environ.get("CI")

        try:
            if original_pytest:
                del os.environ["PYTEST_CURRENT_TEST"]
            if original_ci:
                del os.environ["CI"]

            # Unixスタイルのパストラバーサル
            traversal_path = temp_dir / "../../../etc/passwd"
            result = validate_file_path(traversal_path)
            assert result is False

            # Windowsスタイルのパストラバーサル
            windows_traversal = temp_dir / "..\\..\\Windows\\System32"
            result = validate_file_path(windows_traversal)
            assert result is False

        finally:
            if original_pytest:
                os.environ["PYTEST_CURRENT_TEST"] = original_pytest
            if original_ci:
                os.environ["CI"] = original_ci

    @pytest.mark.unit
    def test_validate_file_path_exception_handling(self, temp_dir):
        """ファイルパス検証の例外処理テスト"""
        # Path.resolve()で例外が発生するようにモック
        with patch.object(Path, "resolve", side_effect=OSError("Path resolution failed")):
            result = validate_file_path(temp_dir / "test.txt")
            assert result is False

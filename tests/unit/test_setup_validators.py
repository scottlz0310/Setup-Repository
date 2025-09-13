"""
セットアップ検証機能のテスト

マルチプラットフォームテスト方針に準拠したセットアップ検証機能のテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.setup_validators import (
    SetupValidator,
    check_system_requirements,
    validate_directory_path,
    validate_github_credentials,
    validate_setup_prerequisites,
    validate_user_input,
)
from tests.multiplatform.helpers import (
    get_platform_specific_config,
    verify_current_platform,
)


class TestSetupValidators:
    """セットアップ検証機能のテスト"""

    def test_setup_validator_init(self):
        """セットアップ検証クラスの初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        validator = SetupValidator()

        assert validator.platform_detector is not None
        assert validator.platform_info is not None
        assert isinstance(validator.errors, list)
        assert len(validator.errors) == 0

    def test_validate_github_credentials(self):
        """GitHub認証情報検証テスト"""
        with (
            patch("setup_repo.setup_validators.get_github_user") as mock_user,
            patch("setup_repo.setup_validators.get_github_token") as mock_token,
        ):
            mock_user.return_value = "testuser"
            mock_token.return_value = "test_token"

            result = validate_github_credentials()

            assert result["username"] == "testuser"
            assert result["token"] == "test_token"
            assert result["username_valid"] is True
            assert result["token_valid"] is True

    def test_validate_directory_path_valid(self):
        """有効なディレクトリパス検証テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_directory_path(temp_dir)

            assert result["valid"] is True
            assert result["error"] is None
            assert result["path"] == Path(temp_dir).resolve()

    def test_validate_directory_path_invalid(self):
        """無効なディレクトリパス検証テスト"""
        result = validate_directory_path("")

        assert result["valid"] is False
        assert "パスが空です" in result["error"]
        assert result["path"] is None

    def test_validate_setup_prerequisites(self):
        """セットアップ前提条件検証テスト"""
        with patch("subprocess.run") as mock_run:
            # Gitが利用可能な場合のモック
            mock_run.return_value = Mock(returncode=0, stdout="git version 2.30.0")

            result = validate_setup_prerequisites()

            assert "valid" in result
            assert "errors" in result
            assert "warnings" in result
            assert "python" in result
            assert "git" in result
            assert isinstance(result["errors"], list)
            assert isinstance(result["warnings"], list)

    def test_check_system_requirements(self):
        """システム要件チェックテスト"""
        result = check_system_requirements()

        assert "platform" in result
        assert "display_name" in result
        assert "supported" in result
        assert "disk_space" in result

        assert result["platform"] in ["windows", "linux", "wsl", "macos"]
        assert result["supported"] is True

    def test_validate_user_input_string(self):
        """文字列入力検証テスト"""
        with patch("builtins.input") as mock_input:
            mock_input.return_value = "test_input"

            result = validate_user_input("入力してください: ", "string")

            assert result["valid"] is True
            assert result["value"] == "test_input"
            assert result["error"] is None

    def test_validate_user_input_boolean(self):
        """ブール入力検証テスト"""
        with patch("builtins.input") as mock_input:
            mock_input.return_value = "y"

            result = validate_user_input("はい/いいえ: ", "boolean")

            assert result["valid"] is True
            assert result["value"] is True
            assert result["error"] is None

    def test_validate_user_input_path(self):
        """パス入力検証テスト"""
        with tempfile.TemporaryDirectory() as temp_dir, patch("builtins.input") as mock_input:
            mock_input.return_value = temp_dir

            result = validate_user_input("パスを入力: ", "path")

            assert result["valid"] is True
            assert result["path"] == Path(temp_dir).resolve()

    def test_setup_validator_error_handling(self):
        """セットアップ検証エラーハンドリングテスト"""
        validator = SetupValidator()

        # エラーを追加
        validator.errors.append("テストエラー")

        errors = validator.get_errors()
        assert len(errors) == 1
        assert "テストエラー" in errors

        # エラーをクリア
        validator.clear_errors()
        assert len(validator.get_errors()) == 0

    @pytest.mark.integration
    def test_setup_validators_integration(self):
        """セットアップ検証統合テスト"""
        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        # セットアップ検証クラスのテスト
        validator = SetupValidator()
        assert validator.platform_info.name in ["windows", "linux", "wsl", "macos"]

        # GitHub認証情報検証
        with (
            patch("setup_repo.setup_validators.get_github_user") as mock_user,
            patch("setup_repo.setup_validators.get_github_token") as mock_token,
        ):
            mock_user.return_value = "testuser"
            mock_token.return_value = "test_token"

            creds = validate_github_credentials()
            assert creds["username_valid"] is True
            assert creds["token_valid"] is True

        # システム要件チェック
        sys_req = check_system_requirements()
        assert sys_req["supported"] is True

        # セットアップ前提条件検証
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="git version 2.30.0")
            prereq = validate_setup_prerequisites()
            assert "python" in prereq
            assert "git" in prereq

    @pytest.mark.slow
    def test_validation_performance(self):
        """検証処理のパフォーマンステスト"""
        import time

        start_time = time.time()

        with (
            patch("subprocess.run") as mock_run,
            patch("setup_repo.setup_validators.get_github_user") as mock_user,
            patch("setup_repo.setup_validators.get_github_token") as mock_token,
        ):
            mock_run.return_value = Mock(returncode=0, stdout="git version 2.30.0")
            mock_user.return_value = "testuser"
            mock_token.return_value = "test_token"

            # 複数回実行してパフォーマンスを測定
            for _ in range(10):
                validate_github_credentials()
                validate_setup_prerequisites()
                check_system_requirements()

        elapsed = time.time() - start_time
        assert elapsed < 5.0, f"検証処理が遅すぎます: {elapsed}秒"

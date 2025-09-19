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

    @pytest.mark.unit
    def test_validate_config_valid(self):
        """有効な設定ファイル検証テスト"""
        try:
            from setup_repo.setup_validators import validate_config
        except ImportError:
            pytest.skip("validate_configが利用できません")

        valid_config = {
            "github_user": "testuser",
            "github_token": "ghp_1234567890abcdef",
            "default_branch": "main",
            "auto_push": True,
        }

        result = validate_config(valid_config)

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["config"] == valid_config

    @pytest.mark.unit
    def test_validate_config_missing_required(self):
        """必須フィールド不足の設定ファイル検証テスト"""
        try:
            from setup_repo.setup_validators import validate_config
        except ImportError:
            pytest.skip("validate_configが利用できません")

        invalid_config = {
            "github_user": "",  # 空のユーザー名
            # github_tokenが不足
        }

        result = validate_config(invalid_config)

        assert result["valid"] is False
        assert len(result["errors"]) >= 1
        assert any("必須フィールド" in error for error in result["errors"])

    @pytest.mark.unit
    def test_validate_config_invalid_username(self):
        """無効なGitHubユーザー名の設定ファイル検証テスト"""
        try:
            from setup_repo.setup_validators import validate_config
        except ImportError:
            pytest.skip("validate_configが利用できません")

        invalid_config = {
            "github_user": "invalid-user-name-",  # 無効な形式
            "github_token": "valid_token_12345",
        }

        result = validate_config(invalid_config)

        assert result["valid"] is False
        assert any("GitHub ユーザー名の形式" in error for error in result["errors"])

    @pytest.mark.unit
    def test_validate_config_short_token(self):
        """短いGitHubトークンの設定ファイル検証テスト"""
        try:
            from setup_repo.setup_validators import validate_config
        except ImportError:
            pytest.skip("validate_configが利用できません")

        invalid_config = {
            "github_user": "validuser",
            "github_token": "short",  # 短すぎるトークン
        }

        result = validate_config(invalid_config)

        assert result["valid"] is False
        assert any("トークンが短すぎ" in error for error in result["errors"])

    @pytest.mark.unit
    def test_validate_environment_basic(self):
        """基本的な環境検証テスト"""
        try:
            from setup_repo.setup_validators import validate_environment
        except ImportError:
            pytest.skip("validate_environmentが利用できません")

        result = validate_environment()

        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert "environment" in result

        # Python情報のチェック
        assert "python" in result["environment"]
        python_info = result["environment"]["python"]
        assert "version" in python_info
        assert "executable" in python_info
        assert "valid" in python_info

    def test_validate_setup_prerequisites_old_python(self):
        """古いPythonバージョンのテスト"""
        with patch("sys.version_info", (3, 8, 0)):
            result = validate_setup_prerequisites()

            assert result["valid"] is False
            assert any("Python 3.9以上が必要" in error for error in result["errors"])

    def test_validate_setup_prerequisites_git_not_found(self):
        """Gitがインストールされていない場合のテスト"""
        with patch("setup_repo.setup_validators.safe_subprocess") as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError("git not found")

            result = validate_setup_prerequisites()

            assert result["valid"] is False
            assert any("Git がインストールされていません" in error for error in result["errors"])
            assert result["git"]["available"] is False

    @pytest.mark.unit
    def test_validate_environment_network_check(self):
        """ネットワーク接続チェックの環境検証テスト"""
        try:
            from setup_repo.setup_validators import validate_environment
        except ImportError:
            pytest.skip("validate_environmentが利用できません")

        with patch("socket.create_connection") as mock_socket:
            # ネットワーク接続成功のケース
            mock_socket.return_value = None

            result = validate_environment()

            assert "network" in result["environment"]
            assert result["environment"]["network"]["github_accessible"] is True

    @pytest.mark.unit
    def test_validate_environment_network_failure(self):
        """ネットワーク接続失敗の環境検証テスト"""
        try:
            from setup_repo.setup_validators import validate_environment
        except ImportError:
            pytest.skip("validate_environmentが利用できません")

        with patch("socket.create_connection") as mock_socket:
            # ネットワーク接続失敗のケース
            mock_socket.side_effect = OSError("Connection failed")

            result = validate_environment()

            assert "network" in result["environment"]
            assert result["environment"]["network"]["github_accessible"] is False
            assert any("GitHub への接続" in warning for warning in result["warnings"])

    def test_validate_directory_path_parent_not_exists(self):
        """親ディレクトリが存在しない場合のテスト"""
        # 存在しない親ディレクトリを指定
        invalid_path = "/nonexistent/parent/directory/child"

        result = validate_directory_path(invalid_path)

        assert result["valid"] is False
        assert "親ディレクトリが存在しません" in result["error"]

    def test_validate_directory_path_mkdir_error(self):
        """ディレクトリ作成エラーのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test_dir"

            with patch("pathlib.Path.mkdir") as mock_mkdir:
                mock_mkdir.side_effect = OSError("Permission denied")

                result = validate_directory_path(str(test_path))

                assert result["valid"] is False
                assert "ディレクトリを作成できません" in result["error"]

    def test_validate_directory_path_not_directory(self):
        """ファイルをディレクトリとして指定した場合のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # ファイルを作成
            test_file = Path(temp_dir) / "test_file.txt"
            test_file.write_text("test")

            result = validate_directory_path(str(test_file))

            assert result["valid"] is False
            assert "ディレクトリではありません" in result["error"]

    def test_validate_user_input_empty_required(self):
        """空入力で必須の場合のテスト"""
        with patch("builtins.input") as mock_input:
            mock_input.return_value = ""  # 空入力

            result = validate_user_input("入力: ", "string", required=True)

            assert result["valid"] is False
            assert "入力が必要" in result["error"]

    def test_validate_user_input_boolean_no(self):
        """ブール入力でNoのテスト"""
        with patch("builtins.input") as mock_input:
            mock_input.return_value = "n"

            result = validate_user_input("はい/いいえ: ", "boolean")

            assert result["valid"] is True
            assert result["value"] is False

    def test_validate_user_input_boolean_invalid(self):
        """ブール入力で無効な値のテスト"""
        with patch("builtins.input") as mock_input:
            mock_input.return_value = "invalid"

            result = validate_user_input("はい/いいえ: ", "boolean")

            assert result["valid"] is False
            assert "y/n で回答" in result["error"]

    def test_validate_user_input_unknown_type(self):
        """不明な入力タイプのテスト"""
        with patch("builtins.input") as mock_input:
            mock_input.return_value = "test"

            result = validate_user_input("入力: ", "unknown_type")

            assert result["valid"] is False
            assert "不明な入力タイプ" in result["error"]

    def test_validate_user_input_keyboard_interrupt(self):
        """キーボード中断のテスト"""
        with patch("builtins.input") as mock_input:
            mock_input.side_effect = KeyboardInterrupt()

            result = validate_user_input("入力: ", "string")

            assert result["valid"] is False
            assert "入力が中断" in result["error"]

"""
セットアップバリデーターモジュールのテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from setup_repo.setup_validators import (
    SetupValidator,
    check_system_requirements,
    validate_directory_path,
    validate_github_credentials,
    validate_setup_prerequisites,
    validate_user_input,
)


class TestSetupValidator:
    """SetupValidatorクラスのテスト"""

    def test_validator_creation(self):
        """バリデーターの作成をテスト"""
        validator = SetupValidator()

        assert validator.platform_detector is not None
        assert validator.platform_info is not None
        assert validator.errors == []

    def test_get_errors(self):
        """エラー取得のテスト"""
        validator = SetupValidator()
        validator.errors = ["エラー1", "エラー2"]

        errors = validator.get_errors()

        assert errors == ["エラー1", "エラー2"]
        # 元のリストが変更されないことを確認
        errors.append("エラー3")
        assert validator.errors == ["エラー1", "エラー2"]

    def test_clear_errors(self):
        """エラークリアのテスト"""
        validator = SetupValidator()
        validator.errors = ["エラー1", "エラー2"]

        validator.clear_errors()

        assert validator.errors == []


class TestValidateGithubCredentials:
    """validate_github_credentialsのテスト"""

    @patch("setup_repo.setup_validators.get_github_user")
    @patch("setup_repo.setup_validators.get_github_token")
    def test_validate_github_credentials_both_present(self, mock_token, mock_user):
        """GitHub認証情報（両方あり）のテスト"""
        mock_user.return_value = "testuser"
        mock_token.return_value = "ghp_test_token"

        result = validate_github_credentials()

        assert result["username"] == "testuser"
        assert result["token"] == "ghp_test_token"
        assert result["username_valid"] is True
        assert result["token_valid"] is True

    @patch("setup_repo.setup_validators.get_github_user")
    @patch("setup_repo.setup_validators.get_github_token")
    def test_validate_github_credentials_missing(self, mock_token, mock_user):
        """GitHub認証情報（なし）のテスト"""
        mock_user.return_value = None
        mock_token.return_value = None

        result = validate_github_credentials()

        assert result["username"] is None
        assert result["token"] is None
        assert result["username_valid"] is False
        assert result["token_valid"] is False


class TestValidateDirectoryPath:
    """validate_directory_pathのテスト"""

    def test_validate_directory_path_empty(self):
        """空パスの検証テスト"""
        result = validate_directory_path("")

        assert result["valid"] is False
        assert "空です" in result["error"]
        assert result["path"] is None

    def test_validate_directory_path_existing(self):
        """既存ディレクトリの検証テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_directory_path(temp_dir)

            assert result["valid"] is True
            assert result["error"] is None
            assert result["path"] == Path(temp_dir).resolve()
            assert result["created"] is False

    def test_validate_directory_path_new(self):
        """新規ディレクトリの検証テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"

            result = validate_directory_path(str(new_dir))

            assert result["valid"] is True
            assert result["error"] is None
            assert result["path"] == new_dir.resolve()
            assert result["created"] is True
            assert new_dir.exists()

    def test_validate_directory_path_invalid_parent(self):
        """無効な親ディレクトリのテスト"""
        invalid_path = "/nonexistent/parent/directory"

        result = validate_directory_path(invalid_path)

        assert result["valid"] is False
        assert "親ディレクトリが存在しません" in result["error"]

    def test_validate_directory_path_file_exists(self):
        """ファイルが存在する場合のテスト"""
        with tempfile.NamedTemporaryFile() as temp_file:
            result = validate_directory_path(temp_file.name)

            assert result["valid"] is False
            assert "ディレクトリではありません" in result["error"]


class TestValidateSetupPrerequisites:
    """validate_setup_prerequisitesのテスト"""

    @patch("subprocess.run")
    @patch("sys.version_info", (3, 11, 0))
    def test_validate_setup_prerequisites_all_good(self, mock_run):
        """前提条件（すべて良好）のテスト"""
        # Git, uv, gh すべて利用可能
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="git version 2.34.1"),
            MagicMock(returncode=0, stdout="uv 0.1.0"),
            MagicMock(returncode=0, stdout="gh version 2.20.0"),
        ]

        result = validate_setup_prerequisites()

        assert result["valid"] is True
        assert result["errors"] == []
        assert result["python"]["valid"] is True
        assert result["git"]["available"] is True
        assert result["uv"]["available"] is True
        assert result["gh"]["available"] is True

    @patch("subprocess.run")
    @patch("sys.version_info", (3, 8, 0))
    def test_validate_setup_prerequisites_old_python(self, mock_run):
        """前提条件（古いPython）のテスト"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="git version 2.34.1"),
            FileNotFoundError(),  # uv not found
            FileNotFoundError(),  # gh not found
        ]

        result = validate_setup_prerequisites()

        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "Python 3.9以上が必要です" in result["errors"][0]
        assert result["python"]["valid"] is False

    @patch("subprocess.run")
    @patch("sys.version_info", (3, 11, 0))
    def test_validate_setup_prerequisites_no_git(self, mock_run):
        """前提条件（Git なし）のテスト"""
        mock_run.side_effect = [
            FileNotFoundError(),  # git not found
            FileNotFoundError(),  # uv not found
            FileNotFoundError(),  # gh not found
        ]

        result = validate_setup_prerequisites()

        assert result["valid"] is False
        assert "Git がインストールされていません" in result["errors"]
        assert result["git"]["available"] is False

    @patch("subprocess.run")
    @patch("sys.version_info", (3, 11, 0))
    def test_validate_setup_prerequisites_warnings_only(self, mock_run):
        """前提条件（警告のみ）のテスト"""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="git version 2.34.1"),
            FileNotFoundError(),  # uv not found
            FileNotFoundError(),  # gh not found
        ]

        result = validate_setup_prerequisites()

        assert result["valid"] is True  # エラーはないので有効
        assert result["errors"] == []
        assert len(result["warnings"]) == 2  # uv と gh の警告


class TestCheckSystemRequirements:
    """check_system_requirementsのテスト"""

    def test_check_system_requirements_basic(self):
        """基本的なシステム要件チェックのテスト"""
        result = check_system_requirements()

        assert "platform" in result
        assert "display_name" in result
        assert "supported" in result
        assert result["supported"] is True
        assert "disk_space" in result

    @patch("shutil.disk_usage")
    def test_check_system_requirements_disk_space(self, mock_disk_usage):
        """ディスク容量チェックのテスト"""
        # 2GB の空き容量をシミュレート
        mock_disk_usage.return_value = MagicMock(free=2 * 1024 * 1024 * 1024)

        result = check_system_requirements()

        assert result["disk_space"]["sufficient"] is True
        assert result["disk_space"]["free_gb"] == 2.0

    @patch("shutil.disk_usage")
    def test_check_system_requirements_low_disk_space(self, mock_disk_usage):
        """低ディスク容量のテスト"""
        # 500MB の空き容量をシミュレート
        mock_disk_usage.return_value = MagicMock(free=500 * 1024 * 1024)

        result = check_system_requirements()

        assert result["disk_space"]["sufficient"] is False


class TestValidateUserInput:
    """validate_user_inputのテスト"""

    @patch("builtins.input")
    def test_validate_user_input_string(self, mock_input):
        """文字列入力の検証テスト"""
        mock_input.return_value = "test input"

        result = validate_user_input("Enter text: ", "string")

        assert result["valid"] is True
        assert result["value"] == "test input"
        assert result["error"] is None

    @patch("builtins.input")
    def test_validate_user_input_empty_required(self, mock_input):
        """空入力（必須）の検証テスト"""
        mock_input.return_value = ""

        result = validate_user_input("Enter text: ", "string", required=True)

        assert result["valid"] is False
        assert result["value"] is None
        assert "入力が必要です" in result["error"]

    @patch("builtins.input")
    def test_validate_user_input_empty_with_default(self, mock_input):
        """空入力（デフォルト値あり）の検証テスト"""
        mock_input.return_value = ""

        result = validate_user_input("Enter text: ", "string", default="default_value")

        assert result["valid"] is True
        assert result["value"] == "default_value"
        assert result["error"] is None

    @patch("builtins.input")
    def test_validate_user_input_boolean_yes(self, mock_input):
        """ブール入力（Yes）の検証テスト"""
        mock_input.return_value = "y"

        result = validate_user_input("Continue? (y/n): ", "boolean")

        assert result["valid"] is True
        assert result["value"] is True
        assert result["error"] is None

    @patch("builtins.input")
    def test_validate_user_input_boolean_no(self, mock_input):
        """ブール入力（No）の検証テスト"""
        mock_input.return_value = "n"

        result = validate_user_input("Continue? (y/n): ", "boolean")

        assert result["valid"] is True
        assert result["value"] is False
        assert result["error"] is None

    @patch("builtins.input")
    def test_validate_user_input_boolean_invalid(self, mock_input):
        """ブール入力（無効）の検証テスト"""
        mock_input.return_value = "maybe"

        result = validate_user_input("Continue? (y/n): ", "boolean")

        assert result["valid"] is False
        assert result["value"] is None
        assert "y/n で回答してください" in result["error"]

    @patch("builtins.input")
    def test_validate_user_input_path(self, mock_input):
        """パス入力の検証テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_input.return_value = temp_dir

            result = validate_user_input("Enter path: ", "path")

            assert result["valid"] is True
            assert result["path"] == Path(temp_dir).resolve()

    @patch("builtins.input")
    def test_validate_user_input_keyboard_interrupt(self, mock_input):
        """キーボード割り込みのテスト"""
        mock_input.side_effect = KeyboardInterrupt()

        result = validate_user_input("Enter text: ", "string")

        assert result["valid"] is False
        assert result["value"] is None
        assert "中断されました" in result["error"]

    def test_validate_user_input_unknown_type(self):
        """不明な入力タイプのテスト"""
        with patch("builtins.input", return_value="test"):
            result = validate_user_input("Enter: ", "unknown_type")

            assert result["valid"] is False
            assert "不明な入力タイプ" in result["error"]

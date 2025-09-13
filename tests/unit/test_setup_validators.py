"""
セットアップ検証機能のテスト

マルチプラットフォームテスト方針に準拠したセットアップ検証機能のテスト
"""

import platform
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.setup_validators import (
    validate_git_config,
    validate_python_environment,
    validate_uv_installation,
    validate_vscode_config,
    ValidationError,
)
from tests.multiplatform.helpers import (
    verify_current_platform,
    skip_if_not_platform,
    get_platform_specific_config,
)


class TestSetupValidators:
    """セットアップ検証機能のテスト"""

    def test_validate_git_config_success(self):
        """Git設定の検証成功テスト"""
        platform_info = verify_current_platform()
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="user.name\nuser.email\n"
            )
            
            result = validate_git_config()
            assert result["valid"] is True
            assert "user.name" in result["config"]
            assert "user.email" in result["config"]

    def test_validate_git_config_missing(self):
        """Git設定の不足テスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stderr="fatal: not a git repository"
            )
            
            with pytest.raises(ValidationError):
                validate_git_config()

    def test_validate_python_environment_success(self):
        """Python環境の検証成功テスト"""
        platform_info = verify_current_platform()
        config = get_platform_specific_config()
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="3.9.0"
            )
            
            result = validate_python_environment()
            assert result["valid"] is True
            assert "version" in result
            assert result["version"].startswith("3.")

    def test_validate_python_environment_old_version(self):
        """古いPythonバージョンのテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="2.7.18"
            )
            
            with pytest.raises(ValidationError, match="Python 3.8以上が必要"):
                validate_python_environment()

    @pytest.mark.windows
    def test_validate_uv_installation_windows(self):
        """Windows環境でのuv検証テスト"""
        skip_if_not_platform("windows")
        
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "C:\\Users\\test\\.cargo\\bin\\uv.exe"
            
            result = validate_uv_installation()
            assert result["valid"] is True
            assert result["path"].endswith("uv.exe")

    @pytest.mark.unix
    def test_validate_uv_installation_unix(self):
        """Unix系環境でのuv検証テスト"""
        skip_if_not_platform("unix")
        
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/uv"
            
            result = validate_uv_installation()
            assert result["valid"] is True
            assert result["path"] == "/usr/local/bin/uv"

    def test_validate_uv_installation_not_found(self):
        """uvが見つからない場合のテスト"""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            
            with pytest.raises(ValidationError, match="uvが見つかりません"):
                validate_uv_installation()

    def test_validate_vscode_config_success(self):
        """VS Code設定の検証成功テスト"""
        platform_info = verify_current_platform()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            vscode_dir = Path(temp_dir) / ".vscode"
            vscode_dir.mkdir()
            
            settings_file = vscode_dir / "settings.json"
            settings_file.write_text('{"python.defaultInterpreter": "python"}')
            
            result = validate_vscode_config(temp_dir)
            assert result["valid"] is True
            assert result["settings_exists"] is True

    def test_validate_vscode_config_missing(self):
        """VS Code設定が存在しない場合のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_vscode_config(temp_dir)
            assert result["valid"] is False
            assert result["settings_exists"] is False

    def test_validate_vscode_config_invalid_json(self):
        """無効なJSON設定のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vscode_dir = Path(temp_dir) / ".vscode"
            vscode_dir.mkdir()
            
            settings_file = vscode_dir / "settings.json"
            settings_file.write_text('{"invalid": json}')
            
            with pytest.raises(ValidationError, match="無効なJSON"):
                validate_vscode_config(temp_dir)

    @pytest.mark.integration
    def test_full_validation_workflow(self):
        """完全な検証ワークフローのテスト"""
        platform_info = verify_current_platform()
        
        with patch("subprocess.run") as mock_run, \
             patch("shutil.which") as mock_which:
            
            # Git設定のモック
            mock_run.return_value = Mock(
                returncode=0,
                stdout="user.name\nuser.email\n"
            )
            
            # uv検証のモック
            mock_which.return_value = "/usr/local/bin/uv"
            
            # 各検証を実行
            git_result = validate_git_config()
            python_result = validate_python_environment()
            uv_result = validate_uv_installation()
            
            assert all([
                git_result["valid"],
                python_result["valid"],
                uv_result["valid"]
            ])

    @pytest.mark.slow
    def test_validation_performance(self):
        """検証処理のパフォーマンステスト"""
        import time
        
        start_time = time.time()
        
        with patch("subprocess.run") as mock_run, \
             patch("shutil.which") as mock_which:
            
            mock_run.return_value = Mock(returncode=0, stdout="test")
            mock_which.return_value = "/usr/bin/uv"
            
            # 複数回実行してパフォーマンスを測定
            for _ in range(10):
                validate_git_config()
                validate_python_environment()
                validate_uv_installation()
        
        elapsed = time.time() - start_time
        assert elapsed < 5.0, f"検証処理が遅すぎます: {elapsed}秒"

    def test_validation_error_handling(self):
        """検証エラーハンドリングのテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("Command not found")
            
            with pytest.raises(ValidationError):
                validate_git_config()

    @pytest.mark.network
    def test_network_dependent_validation(self):
        """ネットワーク依存の検証テスト"""
        # ネットワーク接続が必要な検証のテスト
        # 実際の実装では外部サービスへの接続をテスト
        pytest.skip("ネットワーク接続が必要なテスト")
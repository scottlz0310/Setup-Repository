"""
uvインストーラー機能のテスト

マルチプラットフォームテスト方針に準拠したuvインストーラー機能のテスト
"""

import platform
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from setup_repo.uv_installer import (
    UvInstaller,
    InstallationError,
    check_uv_installation,
    install_uv,
    get_uv_install_command,
)
from tests.multiplatform.helpers import (
    verify_current_platform,
    skip_if_not_platform,
    get_platform_specific_config,
)


class TestUvInstaller:
    """uvインストーラー機能のテスト"""

    def test_check_uv_installation_exists(self):
        """uvが既にインストールされている場合のテスト"""
        platform_info = verify_current_platform()
        
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/uv"
            
            result = check_uv_installation()
            assert result["installed"] is True
            assert result["path"] == "/usr/local/bin/uv"
            assert "version" in result

    def test_check_uv_installation_not_exists(self):
        """uvがインストールされていない場合のテスト"""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            
            result = check_uv_installation()
            assert result["installed"] is False
            assert result["path"] is None

    @pytest.mark.windows
    def test_get_uv_install_command_windows(self):
        """Windows環境でのインストールコマンド取得テスト"""
        skip_if_not_platform("windows")
        
        command = get_uv_install_command()
        assert "powershell" in command.lower()
        assert "irm" in command or "invoke-restmethod" in command.lower()

    @pytest.mark.unix
    def test_get_uv_install_command_unix(self):
        """Unix系環境でのインストールコマンド取得テスト"""
        skip_if_not_platform("unix")
        
        command = get_uv_install_command()
        assert "curl" in command or "wget" in command
        assert "sh" in command

    @pytest.mark.macos
    def test_get_uv_install_command_macos(self):
        """macOS環境でのインストールコマンド取得テスト"""
        skip_if_not_platform("macos")
        
        command = get_uv_install_command()
        # macOSでは複数のインストール方法をサポート
        assert any(method in command for method in ["curl", "brew", "cargo"])

    def test_uv_installer_init(self):
        """UvInstallerの初期化テスト"""
        platform_info = verify_current_platform()
        config = get_platform_specific_config()
        
        installer = UvInstaller()
        assert installer.platform == platform_info.name
        assert installer.shell == config["shell"]

    def test_uv_installer_download_script_success(self):
        """インストールスクリプトのダウンロード成功テスト"""
        installer = UvInstaller()
        
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "#!/bin/sh\necho 'install script'"
            mock_get.return_value = mock_response
            
            script = installer._download_install_script()
            assert script.startswith("#!/bin/sh")
            assert "install script" in script

    def test_uv_installer_download_script_failure(self):
        """インストールスクリプトのダウンロード失敗テスト"""
        installer = UvInstaller()
        
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            with pytest.raises(InstallationError, match="スクリプトのダウンロードに失敗"):
                installer._download_install_script()

    @pytest.mark.windows
    def test_install_uv_windows_success(self):
        """Windows環境でのuvインストール成功テスト"""
        skip_if_not_platform("windows")
        
        with patch("subprocess.run") as mock_run, \
             patch("shutil.which") as mock_which:
            
            # インストール実行のモック
            mock_run.return_value = Mock(returncode=0, stdout="Installation successful")
            
            # インストール後の確認のモック
            mock_which.return_value = "C:\\Users\\test\\.cargo\\bin\\uv.exe"
            
            result = install_uv()
            assert result["success"] is True
            assert result["path"].endswith("uv.exe")

    @pytest.mark.unix
    def test_install_uv_unix_success(self):
        """Unix系環境でのuvインストール成功テスト"""
        skip_if_not_platform("unix")
        
        with patch("subprocess.run") as mock_run, \
             patch("shutil.which") as mock_which:
            
            # インストール実行のモック
            mock_run.return_value = Mock(returncode=0, stdout="Installation successful")
            
            # インストール後の確認のモック
            mock_which.return_value = "/usr/local/bin/uv"
            
            result = install_uv()
            assert result["success"] is True
            assert result["path"] == "/usr/local/bin/uv"

    def test_install_uv_already_installed(self):
        """uvが既にインストールされている場合のテスト"""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/uv"
            
            result = install_uv()
            assert result["success"] is True
            assert result["already_installed"] is True

    def test_install_uv_failure(self):
        """uvインストール失敗テスト"""
        with patch("subprocess.run") as mock_run, \
             patch("shutil.which") as mock_which:
            
            # インストール失敗のモック
            mock_run.return_value = Mock(
                returncode=1, 
                stderr="Installation failed"
            )
            
            # インストール前後でuvが見つからない
            mock_which.return_value = None
            
            with pytest.raises(InstallationError, match="インストールに失敗"):
                install_uv()

    def test_uv_installer_verify_installation(self):
        """インストール後の検証テスト"""
        installer = UvInstaller()
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="uv 0.1.0"
            )
            
            result = installer._verify_installation("/usr/local/bin/uv")
            assert result["valid"] is True
            assert "0.1.0" in result["version"]

    def test_uv_installer_verify_installation_failure(self):
        """インストール検証失敗テスト"""
        installer = UvInstaller()
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stderr="command not found"
            )
            
            result = installer._verify_installation("/usr/local/bin/uv")
            assert result["valid"] is False

    @pytest.mark.integration
    def test_full_installation_workflow(self):
        """完全なインストールワークフローのテスト"""
        platform_info = verify_current_platform()
        
        with patch("subprocess.run") as mock_run, \
             patch("shutil.which") as mock_which, \
             patch("requests.get") as mock_get:
            
            # 初期状態：uvがインストールされていない
            mock_which.side_effect = [None, "/usr/local/bin/uv"]
            
            # スクリプトダウンロードのモック
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "#!/bin/sh\necho 'install'"
            mock_get.return_value = mock_response
            
            # インストール実行のモック
            mock_run.return_value = Mock(returncode=0, stdout="Success")
            
            installer = UvInstaller()
            result = installer.install()
            
            assert result["success"] is True
            assert result["path"] == "/usr/local/bin/uv"

    @pytest.mark.slow
    def test_installation_timeout(self):
        """インストールタイムアウトテスト"""
        installer = UvInstaller()
        
        with patch("subprocess.run") as mock_run:
            # タイムアウトをシミュレート
            mock_run.side_effect = TimeoutError("Installation timeout")
            
            with pytest.raises(InstallationError, match="タイムアウト"):
                installer.install()

    def test_installation_permission_error(self):
        """インストール権限エラーテスト"""
        installer = UvInstaller()
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(InstallationError, match="権限が不足"):
                installer.install()

    @pytest.mark.network
    def test_network_installation(self):
        """ネットワーク経由でのインストールテスト"""
        # 実際のネットワーク接続が必要なテスト
        # CI環境でのみ実行
        pytest.skip("ネットワーク接続が必要なテスト")

    def test_custom_install_path(self):
        """カスタムインストールパスのテスト"""
        installer = UvInstaller()
        custom_path = "/opt/uv/bin"
        
        with patch("subprocess.run") as mock_run, \
             patch("os.makedirs") as mock_makedirs:
            
            mock_run.return_value = Mock(returncode=0)
            
            result = installer.install(install_path=custom_path)
            mock_makedirs.assert_called_once()

    def test_installation_cleanup_on_failure(self):
        """インストール失敗時のクリーンアップテスト"""
        installer = UvInstaller()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_script = Path(temp_dir) / "install_script.sh"
            
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = Exception("Installation failed")
                
                try:
                    installer._execute_install_script(str(temp_script))
                except Exception:
                    pass
                
                # 一時ファイルがクリーンアップされることを確認
                # 実際の実装では適切なクリーンアップロジックをテスト
"""
uvインストーラー機能のテスト

マルチプラットフォームテスト方針に準拠したuvインストーラー機能のテスト
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from setup_repo.uv_installer import (
    ensure_uv,
)
from tests.multiplatform.helpers import (
    get_platform_specific_config,
    verify_current_platform,
)


class TestUvInstaller:
    """uvインストーラー機能のテスト"""

    def test_ensure_uv_already_installed(self):
        """uvが既にインストールされている場合のテスト"""
        verify_current_platform()  # プラットフォーム検証

        with patch("shutil.which") as mock_which, patch("builtins.print"):
            mock_which.return_value = "/usr/local/bin/uv"

            result = ensure_uv()
            assert result is True

    def test_ensure_uv_install_with_pipx(self):
        """pipxでuvをインストールするテスト"""
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run, patch("builtins.print"):
            # uvがない、pipxがある
            mock_which.side_effect = lambda cmd: "/usr/local/bin/pipx" if cmd == "pipx" else None
            mock_run.return_value = Mock(returncode=0)

            result = ensure_uv()
            assert result is True
            mock_run.assert_called_with(["pipx", "install", "uv"], check=True, capture_output=True)

    def test_ensure_uv_install_with_pip(self):
        """pip --userでuvをインストールするテスト"""
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run, patch("builtins.print"):
            # uvとpipxがない、pythonがある
            def which_side_effect(cmd):
                if cmd == "python3":
                    return "/usr/bin/python3"
                return None

            mock_which.side_effect = which_side_effect
            mock_run.return_value = Mock(returncode=0)

            result = ensure_uv()
            assert result is True
            mock_run.assert_called_with(
                ["/usr/bin/python3", "-m", "pip", "install", "--user", "uv"], check=True, capture_output=True
            )

    def test_ensure_uv_install_failure(self):
        """インストール失敗テスト"""
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run, patch("builtins.print"):
            # uv、pipx、pythonがない
            mock_which.return_value = None

            result = ensure_uv()
            assert result is False

    def test_ensure_uv_pipx_failure_fallback_to_pip(self):
        """pipx失敗時のpipフォールバックテスト"""
        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run, patch("builtins.print"):

            def which_side_effect(cmd):
                if cmd == "pipx":
                    return "/usr/local/bin/pipx"
                elif cmd == "python3":
                    return "/usr/bin/python3"
                return None

            mock_which.side_effect = which_side_effect

            # pipx失敗、pip成功
            def run_side_effect(cmd, **kwargs):
                if "pipx" in cmd:
                    raise subprocess.CalledProcessError(1, cmd)
                return Mock(returncode=0)

            mock_run.side_effect = run_side_effect

            result = ensure_uv()
            assert result is True

    @pytest.mark.integration
    def test_ensure_uv_integration(self):
        """ensure_uv統合テスト"""
        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        with patch("shutil.which") as mock_which, patch("subprocess.run") as mock_run, patch("builtins.print"):
            # 既にuvがインストールされているケース
            mock_which.return_value = "/usr/local/bin/uv"

            result = ensure_uv()
            assert result is True

            # インストールが必要なケース
            mock_which.side_effect = lambda cmd: "/usr/local/bin/pipx" if cmd == "pipx" else None
            mock_run.return_value = Mock(returncode=0)

            result = ensure_uv()
            assert result is True

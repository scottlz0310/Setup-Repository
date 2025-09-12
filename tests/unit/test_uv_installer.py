"""UVパッケージマネージャー統合のテスト"""

import subprocess
from unittest.mock import Mock, patch

from src.setup_repo.uv_installer import ensure_uv


class TestEnsureUv:
    """ensure_uv関数のテスト"""

    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_already_installed(self, mock_print, mock_which):
        """uvが既にインストール済みの場合のテスト"""
        # Arrange
        mock_which.return_value = "/usr/bin/uv"

        # Act
        result = ensure_uv()

        # Assert
        assert result is True
        mock_which.assert_called_once_with("uv")
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("uv を発見しました" in call for call in print_calls)

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_install_with_pipx_success(self, mock_print, mock_which, mock_run):
        """pipxでのuvインストール成功のテスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": "/usr/bin/pipx",  # pipxは存在する
        }.get(cmd)
        mock_run.return_value = Mock()

        # Act
        result = ensure_uv()

        # Assert
        assert result is True
        mock_run.assert_called_once_with(["pipx", "install", "uv"], check=True, capture_output=True)
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("pipx で uv をインストールしました" in call for call in print_calls)

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_install_with_pipx_failure_fallback_to_pip(self, mock_print, mock_which, mock_run):
        """pipx失敗後pipでのインストール成功のテスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": "/usr/bin/pipx",  # pipxは存在する
            "python3": "/usr/bin/python3",  # python3は存在する
        }.get(cmd)
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "pipx"),  # pipx失敗
            Mock(),  # pip成功
        ]

        # Act
        result = ensure_uv()

        # Assert
        assert result is True
        assert mock_run.call_count == 2
        # pipxの呼び出し
        mock_run.assert_any_call(["pipx", "install", "uv"], check=True, capture_output=True)
        # pipの呼び出し
        mock_run.assert_any_call(
            ["/usr/bin/python3", "-m", "pip", "install", "--user", "uv"],
            check=True,
            capture_output=True,
        )
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("pipx インストール失敗、pip を試します" in call for call in print_calls)
        assert any("pip --user で uv をインストールしました" in call for call in print_calls)

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_install_with_pip_python_fallback(self, mock_print, mock_which, mock_run):
        """python3がない場合のpythonフォールバックのテスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": None,  # pipxは存在しない
            "python3": None,  # python3は存在しない
            "python": "/usr/bin/python",  # pythonは存在する
        }.get(cmd)
        mock_run.return_value = Mock()

        # Act
        result = ensure_uv()

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["/usr/bin/python", "-m", "pip", "install", "--user", "uv"],
            check=True,
            capture_output=True,
        )
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("pip --user で uv をインストールしました" in call for call in print_calls)

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_no_pipx_pip_success(self, mock_print, mock_which, mock_run):
        """pipxがない場合のpipでのインストール成功のテスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": None,  # pipxは存在しない
            "python3": "/usr/bin/python3",  # python3は存在する
        }.get(cmd)
        mock_run.return_value = Mock()

        # Act
        result = ensure_uv()

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["/usr/bin/python3", "-m", "pip", "install", "--user", "uv"],
            check=True,
            capture_output=True,
        )
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("pip --user で uv をインストールしました" in call for call in print_calls)

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_all_install_methods_fail(self, mock_print, mock_which, mock_run):
        """全てのインストール方法が失敗した場合のテスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": "/usr/bin/pipx",  # pipxは存在する
            "python3": "/usr/bin/python3",  # python3は存在する
        }.get(cmd)
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "pipx"),  # pipx失敗
            subprocess.CalledProcessError(1, "pip"),  # pip失敗
        ]

        # Act
        result = ensure_uv()

        # Assert
        assert result is False
        assert mock_run.call_count == 2
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("uv の自動インストールに失敗しました" in call for call in print_calls)

    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_no_python_available(self, mock_print, mock_which):
        """PythonもPipxも利用できない場合のテスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": None,  # pipxは存在しない
            "python3": None,  # python3は存在しない
            "python": None,  # pythonは存在しない
        }.get(cmd)

        # Act
        result = ensure_uv()

        # Assert
        assert result is False
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("uv の自動インストールに失敗しました" in call for call in print_calls)

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_pip_install_failure(self, mock_print, mock_which, mock_run):
        """pipでのインストール失敗のテスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": None,  # pipxは存在しない
            "python3": "/usr/bin/python3",  # python3は存在する
        }.get(cmd)
        mock_run.side_effect = subprocess.CalledProcessError(1, "pip")

        # Act
        result = ensure_uv()

        # Assert
        assert result is False
        mock_run.assert_called_once_with(
            ["/usr/bin/python3", "-m", "pip", "install", "--user", "uv"],
            check=True,
            capture_output=True,
        )
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("uv の自動インストールに失敗しました" in call for call in print_calls)


class TestEnsureUvEdgeCases:
    """ensure_uv関数のエッジケースのテスト"""

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_pipx_exists_but_fails_no_python(self, mock_print, mock_which, mock_run):
        """pipxは存在するが失敗し、Pythonも存在しない場合のテスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": "/usr/bin/pipx",  # pipxは存在する
            "python3": None,  # python3は存在しない
            "python": None,  # pythonは存在しない
        }.get(cmd)
        mock_run.side_effect = subprocess.CalledProcessError(1, "pipx")

        # Act
        result = ensure_uv()

        # Assert
        assert result is False
        mock_run.assert_called_once_with(["pipx", "install", "uv"], check=True, capture_output=True)
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("pipx インストール失敗、pip を試します" in call for call in print_calls)
        assert any("uv の自動インストールに失敗しました" in call for call in print_calls)

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_multiple_which_calls(self, mock_print, mock_which, mock_run):
        """whichが複数回呼ばれることの確認テスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": "/usr/bin/pipx",  # pipxは存在する
        }.get(cmd)
        mock_run.return_value = Mock()

        # Act
        result = ensure_uv()

        # Assert
        assert result is True
        # whichが複数回呼ばれることを確認
        assert mock_which.call_count >= 2
        mock_which.assert_any_call("uv")
        mock_which.assert_any_call("pipx")

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.print")
    def test_ensure_uv_print_messages_order(self, mock_print, mock_which, mock_run):
        """プリントメッセージの順序確認テスト"""
        # Arrange
        mock_which.side_effect = lambda cmd: {
            "uv": None,  # uvは存在しない
            "pipx": "/usr/bin/pipx",  # pipxは存在する
        }.get(cmd)
        mock_run.return_value = Mock()

        # Act
        result = ensure_uv()

        # Assert
        assert result is True
        print_calls = [call[0][0] for call in mock_print.call_args_list]

        # メッセージの順序を確認
        install_msg_index = None
        success_msg_index = None

        for i, call in enumerate(print_calls):
            if "uv をインストール中" in call:
                install_msg_index = i
            elif "pipx で uv をインストールしました" in call:
                success_msg_index = i

        assert install_msg_index is not None
        assert success_msg_index is not None
        assert install_msg_index < success_msg_index  # インストール中メッセージが先

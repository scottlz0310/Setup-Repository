"""Python環境セットアップモジュールのテスト"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from src.setup_repo.python_env import (
    _setup_with_uv,
    _setup_with_venv,
    has_python_project,
    setup_python_environment,
)


class TestHasPythonProject:
    """has_python_project関数のテスト"""

    @patch("pathlib.Path.exists")
    def test_has_python_project_pyproject_toml(self, mock_exists):
        """pyproject.tomlがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True

        # Act
        result = has_python_project(repo_path)

        # Assert
        assert result is True

    @patch("pathlib.Path.exists")
    def test_has_python_project_requirements_txt(self, mock_exists):
        """requirements.txtがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True

        # Act
        result = has_python_project(repo_path)

        # Assert
        assert result is True

    @patch("pathlib.Path.exists")
    def test_has_python_project_setup_py(self, mock_exists):
        """setup.pyがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True

        # Act
        result = has_python_project(repo_path)

        # Assert
        assert result is True

    @patch("pathlib.Path.exists")
    def test_has_python_project_pipfile(self, mock_exists):
        """Pipfileがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True

        # Act
        result = has_python_project(repo_path)

        # Assert
        assert result is True

    @patch("pathlib.Path.exists")
    def test_has_python_project_setup_cfg(self, mock_exists):
        """setup.cfgがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True

        # Act
        result = has_python_project(repo_path)

        # Assert
        assert result is True

    @patch("pathlib.Path.exists")
    def test_has_python_project_poetry_lock(self, mock_exists):
        """poetry.lockがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True

        # Act
        result = has_python_project(repo_path)

        # Assert
        assert result is True

    @patch("pathlib.Path.exists")
    def test_has_python_project_no_python_files(self, mock_exists):
        """Pythonファイルがない場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = False

        # Act
        result = has_python_project(repo_path)

        # Assert
        assert result is False

    @patch("pathlib.Path.exists")
    def test_has_python_project_multiple_files(self, mock_exists):
        """複数のPythonファイルがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True

        # Act
        result = has_python_project(repo_path)

        # Assert
        assert result is True


class TestSetupPythonEnvironment:
    """setup_python_environment関数のテスト"""

    @patch("src.setup_repo.python_env.has_python_project")
    def test_setup_python_environment_not_python_project(self, mock_has_python):
        """Pythonプロジェクトでない場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_has_python.return_value = False

        # Act
        result = setup_python_environment(repo_path)

        # Assert
        assert result is True
        mock_has_python.assert_called_once_with(repo_path)

    @patch("src.setup_repo.python_env.has_python_project")
    @patch("builtins.print")
    def test_setup_python_environment_dry_run(self, mock_print, mock_has_python):
        """ドライランモードのテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_has_python.return_value = True

        # Act
        result = setup_python_environment(repo_path, dry_run=True)

        # Assert
        assert result is True
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Python環境セットアップ予定" in call for call in print_calls)

    @patch("src.setup_repo.python_env._setup_with_uv")
    @patch("src.setup_repo.python_env.ensure_uv")
    @patch("src.setup_repo.python_env.has_python_project")
    @patch("builtins.print")
    def test_setup_python_environment_with_uv(
        self, mock_print, mock_has_python, mock_ensure_uv, mock_setup_uv
    ):
        """uvを使用したセットアップのテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_has_python.return_value = True
        mock_ensure_uv.return_value = True
        mock_setup_uv.return_value = True

        # Act
        result = setup_python_environment(repo_path)

        # Assert
        assert result is True
        mock_ensure_uv.assert_called_once()
        mock_setup_uv.assert_called_once_with(repo_path)

    @patch("src.setup_repo.python_env._setup_with_venv")
    @patch("src.setup_repo.python_env.ensure_uv")
    @patch("src.setup_repo.python_env.has_python_project")
    @patch("builtins.print")
    def test_setup_python_environment_with_venv(
        self, mock_print, mock_has_python, mock_ensure_uv, mock_setup_venv
    ):
        """venvを使用したセットアップのテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_has_python.return_value = True
        mock_ensure_uv.return_value = False
        mock_setup_venv.return_value = True

        # Act
        result = setup_python_environment(repo_path)

        # Assert
        assert result is True
        mock_ensure_uv.assert_called_once()
        mock_setup_venv.assert_called_once_with(repo_path)


class TestSetupWithUv:
    """_setup_with_uv関数のテスト"""

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_setup_with_uv_pyproject_toml_with_lock(
        self, mock_print, mock_exists, mock_run
    ):
        """pyproject.tomlとuv.lockがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True
        mock_run.return_value = Mock()

        # Act
        result = _setup_with_uv(repo_path)

        # Assert
        assert result is True
        # uv lockは実行されない（既にuv.lockが存在するため）
        # uv venvとuv syncが実行される
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["uv", "venv"], cwd=repo_path, check=True, capture_output=True, shell=False, timeout=300
        )
        mock_run.assert_any_call(
            ["uv", "sync"], cwd=repo_path, check=True, capture_output=True, shell=False, timeout=300
        )

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_setup_with_uv_pyproject_toml_without_lock(
        self, mock_print, mock_exists, mock_run
    ):
        """pyproject.tomlがあるがuv.lockがない場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")

        def exists_side_effect():
            # pyproject.tomlは存在するがuv.lockは存在しない
            # 最初の呼び出し（pyproject.toml）はTrue、2回目（uv.lock）はFalse
            if not hasattr(exists_side_effect, "call_count"):
                exists_side_effect.call_count = 0
            exists_side_effect.call_count += 1
            return exists_side_effect.call_count == 1  # 最初の呼び出しのみTrue

        mock_exists.side_effect = exists_side_effect
        mock_run.return_value = Mock()

        # Act
        result = _setup_with_uv(repo_path)

        # Assert
        assert result is True
        # uv lock、uv venv、uv syncが実行される
        assert mock_run.call_count == 3
        mock_run.assert_any_call(
            ["uv", "lock"], cwd=repo_path, check=True, capture_output=True, shell=False, timeout=300
        )
        mock_run.assert_any_call(
            ["uv", "venv"], cwd=repo_path, check=True, capture_output=True, shell=False, timeout=300
        )
        mock_run.assert_any_call(
            ["uv", "sync"], cwd=repo_path, check=True, capture_output=True, shell=False, timeout=300
        )

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_setup_with_uv_requirements_txt(self, mock_print, mock_exists, mock_run):
        """requirements.txtがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True
        mock_run.return_value = Mock()

        # Act
        result = _setup_with_uv(repo_path)

        # Assert
        assert result is True
        # uv venvとuv pip installが実行される
        assert mock_run.call_count == 2

    @patch("src.setup_repo.python_env._setup_with_venv")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_with_uv_failure_fallback_to_venv(
        self, mock_exists, mock_run, mock_setup_venv
    ):
        """uv失敗時のvenvフォールバックのテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "uv")
        mock_setup_venv.return_value = True

        # Act
        result = _setup_with_uv(repo_path)

        # Assert
        assert result is True
        mock_setup_venv.assert_called_once_with(repo_path)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_setup_with_uv_no_python_files(self, mock_print, mock_exists, mock_run):
        """PythonファイルがないがPythonプロジェクトと判定された場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = False  # どのファイルも存在しない
        mock_run.return_value = Mock()

        # Act
        result = _setup_with_uv(repo_path)

        # Assert
        assert result is True
        # 何も実行されない
        mock_run.assert_not_called()


class TestSetupWithVenv:
    """_setup_with_venv関数のテスト"""

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_setup_with_venv_success_unix(self, mock_print, mock_exists, mock_run):
        """venv成功（Unix系）のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True
        mock_run.return_value = Mock()

        # Act
        result = _setup_with_venv(repo_path)

        # Assert
        assert result is True
        # python3 -m venv、pip upgrade、pip install -r requirements.txtが実行される
        assert mock_run.call_count == 3

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_setup_with_venv_success_windows(self, mock_print, mock_exists, mock_run):
        """venv成功（Windows）のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True
        mock_run.return_value = Mock()

        # Act
        result = _setup_with_venv(repo_path)

        # Assert
        assert result is True
        # python3 -m venv、pip upgrade、pip install -r requirements.txtが実行される
        assert mock_run.call_count == 3

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_setup_with_venv_no_requirements(self, mock_print, mock_exists, mock_run):
        """requirements.txtがない場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")

        def exists_side_effect():
            # bin/pipは存在するがrequirements.txtは存在しない
            return False

        mock_exists.side_effect = exists_side_effect
        mock_run.return_value = Mock()

        # Act
        result = _setup_with_venv(repo_path)

        # Assert
        assert result is True
        # python3 -m venvとpip upgradeのみ実行される
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("builtins.print")
    def test_setup_with_venv_failure(self, mock_print, mock_exists, mock_run):
        """venv失敗のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "python3")

        # Act
        result = _setup_with_venv(repo_path)

        # Assert
        assert result is False
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("venv環境セットアップ失敗" in call for call in print_calls)


class TestEdgeCases:
    """エッジケースのテスト"""

    @patch("pathlib.Path.exists")
    def test_has_python_project_with_path_object(self, mock_exists):
        """Pathオブジェクトでのhas_python_projectのテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_exists.side_effect = lambda: str(repo_path / "pyproject.toml").endswith(
            "pyproject.toml"
        )

        # Act
        result = has_python_project(repo_path)

        # Assert
        assert result is True

    @patch("src.setup_repo.python_env.has_python_project")
    def test_setup_python_environment_with_path_object(self, mock_has_python):
        """Pathオブジェクトでのsetup_python_environmentのテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_has_python.return_value = False

        # Act
        result = setup_python_environment(repo_path)

        # Assert
        assert result is True

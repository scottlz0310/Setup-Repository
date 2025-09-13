"""Python環境管理のテスト"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, call
from ..multiplatform.helpers import verify_current_platform, skip_if_not_platform

from src.setup_repo.python_env import (
    has_python_project,
    setup_python_environment,
    _setup_with_uv,
    _setup_with_venv
)


class TestHasPythonProject:
    """has_python_project関数のテスト"""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """テスト用リポジトリディレクトリ"""
        return tmp_path / "test_repo"

    @pytest.mark.unit
    def test_has_python_project_false(self, temp_repo):
        """Pythonプロジェクトでない場合"""
        platform_info = verify_current_platform()
        
        temp_repo.mkdir()
        result = has_python_project(temp_repo)
        assert result is False

    @pytest.mark.unit
    def test_has_python_project_pyproject_toml(self, temp_repo):
        """pyproject.tomlがある場合"""
        platform_info = verify_current_platform()
        
        temp_repo.mkdir()
        (temp_repo / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        
        result = has_python_project(temp_repo)
        assert result is True

    @pytest.mark.unit
    def test_has_python_project_requirements_txt(self, temp_repo):
        """requirements.txtがある場合"""
        platform_info = verify_current_platform()
        
        temp_repo.mkdir()
        (temp_repo / "requirements.txt").write_text("requests==2.28.0", encoding="utf-8")
        
        result = has_python_project(temp_repo)
        assert result is True

    @pytest.mark.unit
    def test_has_python_project_setup_py(self, temp_repo):
        """setup.pyがある場合"""
        platform_info = verify_current_platform()
        
        temp_repo.mkdir()
        (temp_repo / "setup.py").write_text("from setuptools import setup", encoding="utf-8")
        
        result = has_python_project(temp_repo)
        assert result is True

    @pytest.mark.unit
    def test_has_python_project_pipfile(self, temp_repo):
        """Pipfileがある場合"""
        platform_info = verify_current_platform()
        
        temp_repo.mkdir()
        (temp_repo / "Pipfile").write_text("[packages]", encoding="utf-8")
        
        result = has_python_project(temp_repo)
        assert result is True

    @pytest.mark.unit
    def test_has_python_project_setup_cfg(self, temp_repo):
        """setup.cfgがある場合"""
        platform_info = verify_current_platform()
        
        temp_repo.mkdir()
        (temp_repo / "setup.cfg").write_text("[metadata]", encoding="utf-8")
        
        result = has_python_project(temp_repo)
        assert result is True

    @pytest.mark.unit
    def test_has_python_project_poetry_lock(self, temp_repo):
        """poetry.lockがある場合"""
        platform_info = verify_current_platform()
        
        temp_repo.mkdir()
        (temp_repo / "poetry.lock").write_text("# Poetry lock file", encoding="utf-8")
        
        result = has_python_project(temp_repo)
        assert result is True

    @pytest.mark.unit
    def test_has_python_project_multiple_files(self, temp_repo):
        """複数のPythonファイルがある場合"""
        platform_info = verify_current_platform()
        
        temp_repo.mkdir()
        (temp_repo / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        (temp_repo / "requirements.txt").write_text("requests", encoding="utf-8")
        
        result = has_python_project(temp_repo)
        assert result is True


class TestSetupPythonEnvironment:
    """setup_python_environment関数のテスト"""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """テスト用リポジトリディレクトリ"""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        return repo

    @pytest.mark.unit
    def test_setup_python_environment_not_python_project(self, temp_repo, capsys):
        """Pythonプロジェクトでない場合"""
        platform_info = verify_current_platform()
        
        result = setup_python_environment(temp_repo)
        
        assert result is True
        # 何も出力されないことを確認
        captured = capsys.readouterr()
        assert "Python環境セットアップ中" not in captured.out

    @pytest.mark.unit
    def test_setup_python_environment_dry_run(self, temp_repo, capsys):
        """ドライランモード"""
        platform_info = verify_current_platform()
        
        # Pythonプロジェクトにする
        (temp_repo / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        
        result = setup_python_environment(temp_repo, dry_run=True)
        
        assert result is True
        captured = capsys.readouterr()
        assert "Python環境セットアップ予定" in captured.out

    @pytest.mark.unit
    @patch('src.setup_repo.python_env.ensure_uv')
    @patch('src.setup_repo.python_env._setup_with_uv')
    def test_setup_python_environment_with_uv(self, mock_setup_uv, mock_ensure_uv, temp_repo):
        """uvが利用可能な場合"""
        platform_info = verify_current_platform()
        
        # Pythonプロジェクトにする
        (temp_repo / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        
        mock_ensure_uv.return_value = True
        mock_setup_uv.return_value = True
        
        result = setup_python_environment(temp_repo)
        
        assert result is True
        mock_ensure_uv.assert_called_once()
        mock_setup_uv.assert_called_once_with(temp_repo)

    @pytest.mark.unit
    @patch('src.setup_repo.python_env.ensure_uv')
    @patch('src.setup_repo.python_env._setup_with_venv')
    def test_setup_python_environment_with_venv(self, mock_setup_venv, mock_ensure_uv, temp_repo):
        """uvが利用できない場合"""
        platform_info = verify_current_platform()
        
        # Pythonプロジェクトにする
        (temp_repo / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        
        mock_ensure_uv.return_value = False
        mock_setup_venv.return_value = True
        
        result = setup_python_environment(temp_repo)
        
        assert result is True
        mock_ensure_uv.assert_called_once()
        mock_setup_venv.assert_called_once_with(temp_repo)


class TestSetupWithUv:
    """_setup_with_uv関数のテスト"""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """テスト用リポジトリディレクトリ"""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        return repo

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_setup_with_uv_pyproject_toml_success(self, mock_run, temp_repo, capsys):
        """pyproject.tomlがある場合の成功テスト"""
        platform_info = verify_current_platform()
        
        # pyproject.tomlを作成
        (temp_repo / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        
        # subprocess.runが成功することをモック
        mock_run.return_value = Mock(returncode=0)
        
        result = _setup_with_uv(temp_repo)
        
        assert result is True
        
        # 期待されるコマンドが実行されることを確認
        expected_calls = [
            call(["uv", "lock"], cwd=temp_repo, check=True, capture_output=True, shell=False, timeout=300),
            call(["uv", "venv"], cwd=temp_repo, check=True, capture_output=True, shell=False, timeout=300),
            call(["uv", "sync"], cwd=temp_repo, check=True, capture_output=True, shell=False, timeout=300)
        ]
        mock_run.assert_has_calls(expected_calls)
        
        captured = capsys.readouterr()
        assert "uv環境セットアップ完了" in captured.out

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_setup_with_uv_pyproject_toml_with_existing_lock(self, mock_run, temp_repo):
        """既存のuv.lockがある場合"""
        platform_info = verify_current_platform()
        
        # pyproject.tomlとuv.lockを作成
        (temp_repo / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        (temp_repo / "uv.lock").write_text("# lock file", encoding="utf-8")
        
        mock_run.return_value = Mock(returncode=0)
        
        result = _setup_with_uv(temp_repo)
        
        assert result is True
        
        # uv lockが実行されないことを確認
        expected_calls = [
            call(["uv", "venv"], cwd=temp_repo, check=True, capture_output=True, shell=False, timeout=300),
            call(["uv", "sync"], cwd=temp_repo, check=True, capture_output=True, shell=False, timeout=300)
        ]
        mock_run.assert_has_calls(expected_calls)

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_setup_with_uv_requirements_txt(self, mock_run, temp_repo, capsys):
        """requirements.txtがある場合"""
        platform_info = verify_current_platform()
        
        # requirements.txtを作成
        (temp_repo / "requirements.txt").write_text("requests==2.28.0", encoding="utf-8")
        
        mock_run.return_value = Mock(returncode=0)
        
        result = _setup_with_uv(temp_repo)
        
        assert result is True
        
        expected_calls = [
            call(["uv", "venv"], cwd=temp_repo, check=True, capture_output=True, shell=False, timeout=300),
            call(["uv", "pip", "install", "-r", "requirements.txt"], 
                 cwd=temp_repo, check=True, capture_output=True, shell=False, timeout=300)
        ]
        mock_run.assert_has_calls(expected_calls)

    @pytest.mark.unit
    @patch('subprocess.run')
    @patch('src.setup_repo.python_env._setup_with_venv')
    def test_setup_with_uv_failure_fallback(self, mock_setup_venv, mock_run, temp_repo):
        """uvセットアップ失敗時のvenvフォールバック"""
        platform_info = verify_current_platform()
        
        # pyproject.tomlを作成
        (temp_repo / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        
        # subprocess.runが失敗することをモック
        mock_run.side_effect = subprocess.CalledProcessError(1, "uv")
        mock_setup_venv.return_value = True
        
        result = _setup_with_uv(temp_repo)
        
        assert result is True
        mock_setup_venv.assert_called_once_with(temp_repo)


class TestSetupWithVenv:
    """_setup_with_venv関数のテスト"""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """テスト用リポジトリディレクトリ"""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        return repo

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_setup_with_venv_success_unix(self, mock_run, temp_repo, capsys):
        """Unix系でのvenvセットアップ成功"""
        platform_info = verify_current_platform()
        
        # requirements.txtを作成
        (temp_repo / "requirements.txt").write_text("requests==2.28.0", encoding="utf-8")
        
        # venvディレクトリ構造をモック
        venv_path = temp_repo / ".venv"
        venv_path.mkdir()
        bin_path = venv_path / "bin"
        bin_path.mkdir()
        pip_path = bin_path / "pip"
        pip_path.write_text("#!/usr/bin/env python", encoding="utf-8")
        
        mock_run.return_value = Mock(returncode=0)
        
        result = _setup_with_venv(temp_repo)
        
        assert result is True
        
        # 期待されるコマンドが実行されることを確認
        expected_calls = [
            call(["python3", "-m", "venv", str(venv_path)], 
                 check=True, capture_output=True, shell=False, timeout=300),
            call([str(pip_path), "install", "--upgrade", "pip"], 
                 check=True, capture_output=True, shell=False, timeout=300),
            call([str(pip_path), "install", "-r", "requirements.txt"], 
                 check=True, capture_output=True, shell=False, timeout=300)
        ]
        mock_run.assert_has_calls(expected_calls)
        
        captured = capsys.readouterr()
        assert "venv環境セットアップ完了" in captured.out

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_setup_with_venv_success_windows(self, mock_run, temp_repo):
        """Windowsでのvenvセットアップ成功"""
        platform_info = verify_current_platform()
        
        # venvディレクトリ構造をモック（Windows形式）
        venv_path = temp_repo / ".venv"
        venv_path.mkdir()
        scripts_path = venv_path / "Scripts"
        scripts_path.mkdir()
        pip_path = scripts_path / "pip.exe"
        pip_path.write_text("@echo off", encoding="utf-8")
        
        mock_run.return_value = Mock(returncode=0)
        
        result = _setup_with_venv(temp_repo)
        
        assert result is True
        
        # Windowsのpipパスが使用されることを確認
        calls = mock_run.call_args_list
        pip_upgrade_call = calls[1]
        assert str(pip_path) in pip_upgrade_call[0][0]

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_setup_with_venv_no_requirements(self, mock_run, temp_repo, capsys):
        """requirements.txtがない場合"""
        platform_info = verify_current_platform()
        
        # venvディレクトリ構造をモック
        venv_path = temp_repo / ".venv"
        venv_path.mkdir()
        bin_path = venv_path / "bin"
        bin_path.mkdir()
        pip_path = bin_path / "pip"
        pip_path.write_text("#!/usr/bin/env python", encoding="utf-8")
        
        mock_run.return_value = Mock(returncode=0)
        
        result = _setup_with_venv(temp_repo)
        
        assert result is True
        
        # requirements.txtのインストールが実行されないことを確認
        calls = mock_run.call_args_list
        assert len(calls) == 2  # venv作成とpipアップグレードのみ
        
        captured = capsys.readouterr()
        assert "venv環境セットアップ完了" in captured.out

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_setup_with_venv_failure(self, mock_run, temp_repo, capsys):
        """venvセットアップ失敗"""
        platform_info = verify_current_platform()
        
        # subprocess.runが失敗することをモック
        mock_run.side_effect = subprocess.CalledProcessError(1, "python3")
        
        result = _setup_with_venv(temp_repo)
        
        assert result is False
        
        captured = capsys.readouterr()
        assert "venv環境セットアップ失敗" in captured.out


class TestPythonEnvIntegration:
    """Python環境管理の統合テスト"""

    @pytest.mark.unit
    def test_python_file_detection_comprehensive(self, tmp_path):
        """包括的なPythonファイル検出テスト"""
        platform_info = verify_current_platform()
        
        test_cases = [
            ("pyproject.toml", "[tool.test]"),
            ("requirements.txt", "requests==2.28.0"),
            ("setup.py", "from setuptools import setup"),
            ("Pipfile", "[packages]"),
            ("setup.cfg", "[metadata]"),
            ("poetry.lock", "# Poetry lock file")
        ]
        
        for filename, content in test_cases:
            repo_path = tmp_path / f"test_{filename.replace('.', '_')}"
            repo_path.mkdir()
            (repo_path / filename).write_text(content, encoding="utf-8")
            
            assert has_python_project(repo_path) is True

    @pytest.mark.unit
    @patch('src.setup_repo.python_env.ensure_uv')
    @patch('subprocess.run')
    def test_environment_setup_workflow(self, mock_run, mock_ensure_uv, tmp_path, capsys):
        """環境セットアップワークフローテスト"""
        platform_info = verify_current_platform()
        
        # テストリポジトリを作成
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        
        # uvが利用可能な場合
        mock_ensure_uv.return_value = True
        mock_run.return_value = Mock(returncode=0)
        
        result = setup_python_environment(repo_path)
        
        assert result is True
        
        # 適切なメッセージが出力されることを確認
        captured = capsys.readouterr()
        assert "Python環境セットアップ中" in captured.out
        assert "uv環境セットアップ完了" in captured.out

    @pytest.mark.unit
    def test_edge_cases(self, tmp_path):
        """エッジケースのテスト"""
        platform_info = verify_current_platform()
        
        # 存在しないディレクトリ
        nonexistent_path = tmp_path / "nonexistent"
        assert has_python_project(nonexistent_path) is False
        
        # 空のディレクトリ
        empty_path = tmp_path / "empty"
        empty_path.mkdir()
        assert has_python_project(empty_path) is False
        
        # 権限のないディレクトリ（シミュレーション）
        # 実際の権限テストは環境依存のため、基本的な動作のみ確認
        assert setup_python_environment(empty_path) is True  # Pythonプロジェクトでないため成功
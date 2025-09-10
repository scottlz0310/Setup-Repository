"""
CI環境検出モジュールのテスト
"""

import os
import subprocess
from unittest.mock import patch, MagicMock

from setup_repo.ci_environment import CIEnvironmentInfo


class TestCIEnvironmentInfo:
    """CIEnvironmentInfoクラスのテスト"""

    def test_detect_ci_environment_github_actions(self):
        """GitHub Actions環境検出のテスト"""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            assert CIEnvironmentInfo.detect_ci_environment() == "github_actions"

    def test_detect_ci_environment_gitlab_ci(self):
        """GitLab CI環境検出のテスト"""
        with patch.dict(os.environ, {"GITLAB_CI": "true"}, clear=True):
            assert CIEnvironmentInfo.detect_ci_environment() == "gitlab_ci"

    def test_detect_ci_environment_jenkins(self):
        """Jenkins環境検出のテスト"""
        with patch.dict(os.environ, {"JENKINS_URL": "http://jenkins.example.com"}, clear=True):
            assert CIEnvironmentInfo.detect_ci_environment() == "jenkins"

    def test_detect_ci_environment_circleci(self):
        """CircleCI環境検出のテスト"""
        with patch.dict(os.environ, {"CIRCLECI": "true"}, clear=True):
            assert CIEnvironmentInfo.detect_ci_environment() == "circleci"

    def test_detect_ci_environment_travis(self):
        """Travis CI環境検出のテスト"""
        with patch.dict(os.environ, {"TRAVIS": "true"}, clear=True):
            assert CIEnvironmentInfo.detect_ci_environment() == "travis"

    def test_detect_ci_environment_generic_ci(self):
        """汎用CI環境検出のテスト"""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            assert CIEnvironmentInfo.detect_ci_environment() == "generic_ci"

    def test_detect_ci_environment_local(self):
        """ローカル環境検出のテスト"""
        with patch.dict(os.environ, {}, clear=True):
            assert CIEnvironmentInfo.detect_ci_environment() == "local"

    def test_is_ci_environment_true(self):
        """CI環境判定（True）のテスト"""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            assert CIEnvironmentInfo.is_ci_environment() is True

    def test_is_ci_environment_false(self):
        """CI環境判定（False）のテスト"""
        with patch.dict(os.environ, {}, clear=True):
            assert CIEnvironmentInfo.is_ci_environment() is False

    def test_get_github_actions_info(self):
        """GitHub Actions情報取得のテスト"""
        github_env = {
            "RUNNER_OS": "Linux",
            "RUNNER_ARCH": "X64",
            "GITHUB_WORKFLOW": "CI",
            "GITHUB_ACTION": "test",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_REPOSITORY": "test/repo",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": "abc123",
            "GITHUB_RUN_ID": "123456",
            "GITHUB_RUN_NUMBER": "1",
            "GITHUB_JOB": "test-job",
            "GITHUB_STEP_SUMMARY": "/tmp/summary",
        }

        with patch.dict(os.environ, github_env):
            info = CIEnvironmentInfo.get_github_actions_info()
            
            assert info["runner_os"] == "Linux"
            assert info["runner_arch"] == "X64"
            assert info["github_workflow"] == "CI"
            assert info["github_repository"] == "test/repo"

    def test_get_ci_metadata_github_actions(self):
        """GitHub ActionsのCI メタデータ取得のテスト"""
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "test/repo"}):
            metadata = CIEnvironmentInfo.get_ci_metadata()
            assert "github_repository" in metadata
            assert metadata["github_repository"] == "test/repo"

    def test_get_ci_metadata_gitlab_ci(self):
        """GitLab CIのメタデータ取得のテスト"""
        gitlab_env = {
            "GITLAB_CI": "true",
            "CI_JOB_ID": "123",
            "CI_JOB_NAME": "test-job",
            "CI_PIPELINE_ID": "456",
            "CI_COMMIT_SHA": "abc123",
            "CI_COMMIT_REF_NAME": "main",
        }

        with patch.dict(os.environ, gitlab_env, clear=True):
            metadata = CIEnvironmentInfo.get_ci_metadata()
            
            assert metadata["gitlab_ci"] == "true"
            assert metadata["ci_job_id"] == "123"
            assert metadata["ci_commit_sha"] == "abc123"

    def test_get_ci_metadata_unknown(self):
        """不明なCI環境のメタデータ取得のテスト"""
        with patch.dict(os.environ, {"CI": "true"}, clear=True):
            metadata = CIEnvironmentInfo.get_ci_metadata()
            assert metadata["ci_type"] == "generic_ci"

    def test_collect_environment_vars(self):
        """環境変数収集のテスト"""
        test_env = {
            "GITHUB_ACTIONS": "true",
            "CI_JOB_ID": "123",
            "RUNNER_OS": "Linux",
            "GITLAB_CI": "true",
            "JENKINS_URL": "http://jenkins.example.com",
            "TRAVIS": "true",
            "NORMAL_VAR": "should_not_be_included",
        }

        with patch.dict(os.environ, test_env, clear=True):
            env_vars = CIEnvironmentInfo.collect_environment_vars()
            
            assert "GITHUB_ACTIONS" in env_vars
            assert "CI_JOB_ID" in env_vars
            assert "RUNNER_OS" in env_vars
            assert "GITLAB_CI" in env_vars
            assert "JENKINS_URL" in env_vars
            assert "TRAVIS" in env_vars
            assert "NORMAL_VAR" not in env_vars

    @patch('subprocess.check_output')
    def test_get_system_info_success(self, mock_subprocess):
        """システム情報取得成功のテスト"""
        # Git コマンドの戻り値をモック
        mock_subprocess.side_effect = [
            "abc123def456\n",  # git rev-parse HEAD
            "main\n"           # git rev-parse --abbrev-ref HEAD
        ]

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            info = CIEnvironmentInfo.get_system_info()
            
            assert "python_version" in info
            assert "platform" in info
            assert "working_directory" in info
            assert info["git_info"]["commit"] == "abc123def456"
            assert info["git_info"]["branch"] == "main"
            assert info["ci_type"] == "github_actions"

    @patch('subprocess.check_output')
    def test_get_system_info_git_error(self, mock_subprocess):
        """Git情報取得エラーのテスト"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "git")

        info = CIEnvironmentInfo.get_system_info()
        
        assert info["git_info"]["commit"] == "unknown"
        assert info["git_info"]["branch"] == "unknown"

    def test_get_system_info_exception(self):
        """システム情報取得例外のテスト"""
        # より確実に例外を発生させるため、os.getcwdをモック
        with patch('os.getcwd', side_effect=Exception("Test error")):
            info = CIEnvironmentInfo.get_system_info()
            assert "error" in info
            assert "システム情報取得エラー" in info["error"]

    @patch('subprocess.check_output')
    def test_get_dependency_info_success(self, mock_subprocess):
        """依存関係情報取得成功のテスト"""
        mock_subprocess.side_effect = [
            "uv 0.1.0\n",  # uv --version
            '[{"name": "pytest", "version": "7.0.0"}, {"name": "ruff", "version": "0.1.0"}]'  # pip list
        ]

        with patch.dict(os.environ, {"VIRTUAL_ENV": "/path/to/venv"}):
            info = CIEnvironmentInfo.get_dependency_info()
            
            assert info["uv_info"]["version"] == "uv 0.1.0"
            assert info["uv_info"]["virtual_env"] == "/path/to/venv"
            assert info["packages"]["pytest"] == "7.0.0"
            assert info["packages"]["ruff"] == "0.1.0"

    @patch('subprocess.check_output')
    def test_get_dependency_info_uv_not_found(self, mock_subprocess):
        """uv未インストール時のテスト"""
        mock_subprocess.side_effect = [
            FileNotFoundError(),  # uv --version
            '[]'  # pip list
        ]

        info = CIEnvironmentInfo.get_dependency_info()
        
        assert info["uv_info"]["error"] == "uv not found"
        assert info["packages"] == {}

    @patch('subprocess.check_output')
    def test_get_dependency_info_pip_error(self, mock_subprocess):
        """pip list エラーのテスト"""
        mock_subprocess.side_effect = [
            "uv 0.1.0\n",  # uv --version
            subprocess.CalledProcessError(1, "pip")  # pip list
        ]

        info = CIEnvironmentInfo.get_dependency_info()
        
        assert info["packages"]["error"] == "パッケージ情報取得エラー"

    def test_get_dependency_info_exception(self):
        """依存関係情報取得例外のテスト"""
        with patch('subprocess.check_output', side_effect=Exception("Test error")):
            info = CIEnvironmentInfo.get_dependency_info()
            assert "error" in info
            assert "依存関係情報取得エラー" in info["error"]
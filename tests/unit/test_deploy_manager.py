"""DeployManagerのテスト."""

import json
from unittest.mock import Mock, patch

import pytest

from setup_repo.deploy_manager import DeployManager


class TestDeployManager:
    """DeployManagerのテストクラス."""

    @pytest.fixture
    def config(self):
        """設定辞書."""
        return {"github_token": "test_token", "owner": "test_owner"}

    @pytest.fixture
    def deploy_manager(self, config, tmp_path):
        """DeployManagerのインスタンス."""
        manager = DeployManager(config)
        manager.deploy_history_file = tmp_path / "deploy_history.json"
        return manager

    @pytest.fixture
    def mock_git_ops(self, deploy_manager):
        """GitOperationsのモック."""
        with patch.object(deploy_manager, "git_ops") as mock:
            mock.is_clean.return_value = True
            mock.get_current_branch.return_value = "main"
            mock.get_current_commit.return_value = "abc123def456"
            yield mock

    def test_prepare_success(self, deploy_manager, mock_git_ops):
        """デプロイ準備の成功テスト."""
        with (
            patch.object(deploy_manager, "_run_quality_checks", return_value=True),
            patch.object(deploy_manager, "_build_project", return_value=True),
        ):
            result = deploy_manager.prepare()
            assert result is True

    def test_prepare_quality_check_failure(self, deploy_manager, mock_git_ops):
        """品質チェック失敗時のテスト."""
        with patch.object(deploy_manager, "_run_quality_checks", return_value=False):
            result = deploy_manager.prepare()
            assert result is False

    def test_prepare_build_failure(self, deploy_manager, mock_git_ops):
        """ビルド失敗時のテスト."""
        with (
            patch.object(deploy_manager, "_run_quality_checks", return_value=True),
            patch.object(deploy_manager, "_build_project", return_value=False),
        ):
            result = deploy_manager.prepare()
            assert result is False

    def test_execute_success(self, deploy_manager, mock_git_ops):
        """デプロイ実行の成功テスト."""
        with (
            patch.object(deploy_manager, "_pre_deploy_check", return_value=True),
            patch.object(deploy_manager, "_execute_deploy", return_value=True),
            patch.object(deploy_manager, "_record_deploy_history"),
        ):
            result = deploy_manager.execute("staging")
            assert result is True

    def test_execute_pre_check_failure(self, deploy_manager, mock_git_ops):
        """デプロイ前チェック失敗時のテスト."""
        with patch.object(deploy_manager, "_pre_deploy_check", return_value=False):
            result = deploy_manager.execute("staging")
            assert result is False

    def test_rollback_success(self, deploy_manager, mock_git_ops):
        """ロールバック成功テスト."""
        target_deploy = {"deploy_id": "deploy_20250127_120000_abc123de"}

        with (
            patch.object(deploy_manager, "_get_rollback_target", return_value=target_deploy),
            patch.object(deploy_manager, "_execute_rollback", return_value=True),
            patch.object(deploy_manager, "_record_deploy_history"),
        ):
            result = deploy_manager.rollback()
            assert result is True

    def test_rollback_no_target(self, deploy_manager, mock_git_ops):
        """ロールバック対象なしのテスト."""
        with patch.object(deploy_manager, "_get_rollback_target", return_value=None):
            result = deploy_manager.rollback()
            assert result is False

    @patch("subprocess.run")
    def test_run_quality_checks_success(self, mock_run, deploy_manager):
        """品質チェック成功テスト."""
        mock_run.return_value = Mock(returncode=0)

        result = deploy_manager._run_quality_checks()
        assert result is True
        assert mock_run.call_count == 4  # 4つのチェック

    @patch("subprocess.run")
    def test_run_quality_checks_failure(self, mock_run, deploy_manager):
        """品質チェック失敗テスト."""
        mock_run.return_value = Mock(returncode=1, stderr="Error")

        result = deploy_manager._run_quality_checks()
        assert result is False

    @patch("subprocess.run")
    def test_build_project_success(self, mock_run, deploy_manager):
        """ビルド成功テスト."""
        mock_run.return_value = Mock(returncode=0)

        result = deploy_manager._build_project()
        assert result is True

    @patch("subprocess.run")
    def test_build_project_failure(self, mock_run, deploy_manager):
        """ビルド失敗テスト."""
        mock_run.return_value = Mock(returncode=1, stderr="Build failed")

        result = deploy_manager._build_project()
        assert result is False

    @patch("subprocess.run")
    def test_build_project_uv_not_found(self, mock_run, deploy_manager):
        """uv未インストール時のテスト."""
        mock_run.side_effect = FileNotFoundError()

        result = deploy_manager._build_project()
        assert result is True  # uvがない場合はスキップして成功

    def test_pre_deploy_check_success(self, deploy_manager, mock_git_ops):
        """デプロイ前チェック成功テスト."""
        result = deploy_manager._pre_deploy_check()
        assert result is True

    def test_pre_deploy_check_dirty_working_dir(self, deploy_manager, mock_git_ops):
        """作業ディレクトリが汚れている場合のテスト."""
        mock_git_ops.is_clean.return_value = False

        result = deploy_manager._pre_deploy_check()
        assert result is False

    def test_generate_deploy_id(self, deploy_manager, mock_git_ops):
        """デプロイID生成テスト."""
        deploy_id = deploy_manager._generate_deploy_id()

        assert deploy_id.startswith("deploy_")
        assert "abc123de" in deploy_id  # コミットハッシュの一部

    def test_record_deploy_history(self, deploy_manager, mock_git_ops):
        """デプロイ履歴記録テスト."""
        deploy_manager._record_deploy_history("production", "deploy_123", "success")

        assert deploy_manager.deploy_history_file.exists()

        with open(deploy_manager.deploy_history_file, encoding="utf-8") as f:
            history = json.load(f)

        assert len(history) == 1
        assert history[0]["deploy_id"] == "deploy_123"
        assert history[0]["environment"] == "production"
        assert history[0]["status"] == "success"

    def test_load_deploy_history_empty(self, deploy_manager):
        """空のデプロイ履歴読み込みテスト."""
        history = deploy_manager._load_deploy_history()
        assert history == []

    def test_load_deploy_history_existing(self, deploy_manager):
        """既存のデプロイ履歴読み込みテスト."""
        test_history = [{"deploy_id": "test_123", "status": "success"}]

        with open(deploy_manager.deploy_history_file, "w", encoding="utf-8") as f:
            json.dump(test_history, f)

        history = deploy_manager._load_deploy_history()
        assert history == test_history

    def test_get_rollback_target_by_id(self, deploy_manager):
        """指定IDでのロールバック対象取得テスト."""
        test_history = [
            {"deploy_id": "deploy_123", "status": "success"},
            {"deploy_id": "deploy_456", "status": "failed"},
        ]

        with open(deploy_manager.deploy_history_file, "w", encoding="utf-8") as f:
            json.dump(test_history, f)

        target = deploy_manager._get_rollback_target("deploy_123")
        assert target["deploy_id"] == "deploy_123"

    def test_get_rollback_target_latest(self, deploy_manager):
        """最新成功デプロイでのロールバック対象取得テスト."""
        test_history = [
            {"deploy_id": "deploy_123", "status": "success", "environment": "production"},
            {"deploy_id": "deploy_456", "status": "failed", "environment": "production"},
        ]

        with open(deploy_manager.deploy_history_file, "w", encoding="utf-8") as f:
            json.dump(test_history, f)

        target = deploy_manager._get_rollback_target()
        assert target["deploy_id"] == "deploy_123"

    def test_list_deployments(self, deploy_manager):
        """デプロイ履歴一覧テスト."""
        test_history = [{"deploy_id": "deploy_123", "status": "success"}]

        with open(deploy_manager.deploy_history_file, "w", encoding="utf-8") as f:
            json.dump(test_history, f)

        deployments = deploy_manager.list_deployments()
        assert deployments == test_history

"""
sync機能の統合テスト

このモジュールでは、sync機能全体の統合テストを実装します。
テスト用リポジトリを使用して、実際のGit操作に近い環境で
sync機能の動作を検証します。
"""

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from setup_repo.sync import SyncResult, sync_repositories


@pytest.mark.integration
class TestSyncIntegration:
    """sync機能の統合テストクラス"""

    def test_complete_sync_workflow(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """完全な同期ワークフローのテスト"""
        # テスト用のクローン先ディレクトリを設定
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 既存のリポジトリディレクトリを作成
        existing_repo = clone_destination / "test-repo-1"
        existing_repo.mkdir(parents=True)
        (existing_repo / ".git").mkdir()

        # モックを設定
        mock_git_operations.is_git_repository.return_value = True
        mock_git_operations.pull_repository.return_value = True

        # sync機能を実行
        with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=False)

        # 結果を検証
        assert isinstance(result, SyncResult)
        assert result.success
        assert len(result.synced_repos) > 0
        assert len(result.errors) == 0

        # モックが適切に呼び出されたことを確認
        mock_github_api.get_user_repos.assert_called()
        mock_git_operations.pull_repository.assert_called()

    def test_sync_with_new_repositories(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """新しいリポジトリの同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 新しいリポジトリのクローンをシミュレート
        mock_git_operations.is_git_repository.return_value = False
        mock_git_operations.clone_repository.return_value = True

        with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=False)

        # 新しいリポジトリがクローンされたことを確認
        assert result.success
        mock_git_operations.clone_repository.assert_called()

        # クローン先ディレクトリが作成されたことを確認
        assert clone_destination.exists()

    def test_sync_with_existing_repositories(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """既存リポジトリの同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 既存のリポジトリを作成
        for repo_name in ["test-repo-1", "test-repo-2"]:
            repo_dir = clone_destination / repo_name
            repo_dir.mkdir(parents=True)
            (repo_dir / ".git").mkdir()

        # 既存リポジトリの更新をシミュレート
        mock_git_operations.is_git_repository.return_value = True
        mock_git_operations.pull_repository.return_value = True

        with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=False)

        # 既存リポジトリが更新されたことを確認
        assert result.success
        mock_git_operations.pull_repository.assert_called()

    def test_sync_dry_run_mode(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """ドライランモードでの同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=True)

        # ドライランモードでは実際の操作は行われない
        assert result.success
        mock_git_operations.clone_repository.assert_not_called()
        mock_git_operations.pull_repository.assert_not_called()

        # ただし、リポジトリ情報の取得は行われる
        mock_github_api.get_user_repos.assert_called()

    def test_sync_with_git_errors(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """Git操作エラー時の同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # Git操作でエラーが発生するようにモックを設定
        mock_git_operations.is_git_repository.return_value = False
        mock_git_operations.clone_repository.return_value = False  # クローン失敗

        with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=False)

        # エラーが適切に処理されることを確認
        assert not result.success
        assert len(result.errors) > 0

    def test_sync_with_network_errors(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_git_operations: Mock,
    ) -> None:
        """ネットワークエラー時の同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # GitHub APIでネットワークエラーをシミュレート
        mock_github_api_error = Mock()
        mock_github_api_error.get_user_repos.side_effect = Exception(
            "ネットワークエラー"
        )

        with patch(
            "setup_repo.github_api.GitHubAPI", return_value=mock_github_api_error
        ):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=False)

        # ネットワークエラーが適切に処理されることを確認
        assert not result.success
        assert len(result.errors) > 0
        assert "ネットワークエラー" in str(result.errors[0])

    def test_sync_with_partial_failures(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """部分的な失敗がある同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 一部のリポジトリでエラーが発生するようにモックを設定
        def mock_clone_side_effect(repo_url: str, destination: str) -> bool:
            # test-repo-1は成功、test-repo-2は失敗
            return "test-repo-1" in repo_url

        mock_git_operations.is_git_repository.return_value = False
        mock_git_operations.clone_repository.side_effect = mock_clone_side_effect

        with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=False)

        # 部分的な成功が記録されることを確認
        assert len(result.synced_repos) > 0  # 成功したリポジトリがある
        assert len(result.errors) > 0  # エラーも発生している

    @pytest.mark.slow
    def test_sync_performance_with_many_repositories(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_git_operations: Mock,
    ) -> None:
        """多数のリポジトリでの同期パフォーマンステスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 多数のリポジトリをシミュレート
        many_repos = [
            {
                "name": f"test-repo-{i}",
                "clone_url": f"https://github.com/test_user/test-repo-{i}.git",
                "description": f"テストリポジトリ{i}",
                "private": False,
                "default_branch": "main",
            }
            for i in range(20)  # 20個のリポジトリ
        ]

        mock_github_api_many = Mock()
        mock_github_api_many.get_user_repos.return_value = many_repos

        mock_git_operations.is_git_repository.return_value = False
        mock_git_operations.clone_repository.return_value = True

        import time

        start_time = time.time()

        with patch(
            "setup_repo.github_api.GitHubAPI", return_value=mock_github_api_many
        ):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=True)

        execution_time = time.time() - start_time

        # パフォーマンス要件: 20リポジトリの同期が10秒以内（ドライランモード）
        assert execution_time < 10.0
        assert result.success
        assert len(result.synced_repos) == 20

    def test_sync_with_file_system_cleanup(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """ファイルシステムクリーンアップを含む同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 古いリポジトリディレクトリを作成
        old_repo = clone_destination / "old-repo"
        old_repo.mkdir(parents=True)
        (old_repo / "old_file.txt").write_text("古いファイル")

        # 現在のリポジトリのみを返すようにモックを設定
        current_repos = [
            {
                "name": "current-repo",
                "clone_url": "https://github.com/test_user/current-repo.git",
                "description": "現在のリポジトリ",
                "private": False,
                "default_branch": "main",
            }
        ]
        mock_github_api.get_user_repos.return_value = current_repos

        mock_git_operations.is_git_repository.return_value = False
        mock_git_operations.clone_repository.return_value = True

        with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=False)

        # 同期が成功したことを確認
        assert result.success

        # 古いリポジトリディレクトリが残っていることを確認
        # （実際のクリーンアップ機能は別途実装される）
        assert old_repo.exists()

    def test_sync_result_serialization(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """同期結果のシリアライゼーションテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        mock_git_operations.is_git_repository.return_value = True
        mock_git_operations.pull_repository.return_value = True

        with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
            with patch(
                "setup_repo.git_operations.GitOperations",
                return_value=mock_git_operations,
            ):
                result = sync_repositories(sample_config, dry_run=False)

        # 結果をJSONにシリアライズできることを確認
        result_dict = {
            "success": result.success,
            "synced_repos": result.synced_repos,
            "errors": [str(error) for error in result.errors],
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
        }

        # JSONシリアライゼーションが成功することを確認
        json_str = json.dumps(result_dict, ensure_ascii=False, indent=2)
        assert json_str is not None
        assert len(json_str) > 0

        # デシリアライゼーションも確認
        deserialized = json.loads(json_str)
        assert deserialized["success"] == result.success
        assert len(deserialized["synced_repos"]) == len(result.synced_repos)

    def test_sync_with_config_validation(
        self,
        temp_dir: Path,
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """設定検証を含む同期テスト"""
        # 無効な設定でテスト
        invalid_configs = [
            {},  # 空の設定
            {"github_token": ""},  # 空のトークン
            {"github_token": "valid_token"},  # ユーザー名なし
            {
                "github_token": "valid_token",
                "github_username": "valid_user",
            },  # クローン先なし
        ]

        for invalid_config in invalid_configs:
            with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
                with patch(
                    "setup_repo.git_operations.GitOperations",
                    return_value=mock_git_operations,
                ):
                    # 無効な設定では同期が失敗することを確認
                    result = sync_repositories(invalid_config, dry_run=True)
                    assert not result.success
                    assert len(result.errors) > 0

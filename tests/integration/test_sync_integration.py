"""
sync機能の統合テスト

このモジュールでは、sync機能全体の統合テストを実装します。
テスト用リポジトリを使用して、実際のGit操作に近い環境で
sync機能の動作を検証します。
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from setup_repo.sync import SyncResult, sync_repositories

from ..multiplatform.helpers import verify_current_platform


@pytest.mark.integration
class TestSyncIntegration:
    """sync機能の統合テストクラス"""

    def test_complete_sync_workflow(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """完全な同期ワークフローのテスト"""
        # プラットフォーム検証を統合
        platform_info = verify_current_platform()

        # テスト用のクローン先ディレクトリを設定
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)
        sample_config["dest"] = str(clone_destination)  # destフィールドも更新

        # 既存のリポジトリディレクトリを作成
        existing_repo = clone_destination / "test-repo-1"
        existing_repo.mkdir(parents=True)
        (existing_repo / ".git").mkdir()

        # モックを設定
        mock_git_operations.is_git_repository.return_value = True
        mock_git_operations.pull_repository.return_value = True

        # sync機能を実行（with統合）
        repos_data = mock_github_api.get_user_repos.return_value
        with (
            patch("setup_repo.sync.get_repositories", return_value=repos_data) as mock_get_repos,
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                return_value=True,
            ) as mock_sync,
        ):
            result = sync_repositories(sample_config, dry_run=False)
        assert isinstance(result, SyncResult)
        assert result.success
        assert result.synced_repos
        assert not result.errors

        # モックが適切に呼び出されたことを確認
        mock_get_repos.assert_called_once()
        assert mock_sync.call_count == 2  # 2つのリポジトリで呼び出される

    def test_sync_with_new_repositories(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """新しいリポジトリの同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)
        sample_config["dest"] = str(clone_destination)  # destフィールドも更新

        def mock_sync_with_retries(repo, dest_dir, config):
            # クローン先ディレクトリを作成
            dest_path = Path(dest_dir)
            dest_path.mkdir(parents=True, exist_ok=True)

            # リポジトリディレクトリを作成
            repo_path = dest_path / repo["name"]
            repo_path.mkdir(parents=True, exist_ok=True)
            (repo_path / ".git").mkdir(exist_ok=True)
            return True

        repos_data = mock_github_api.get_user_repos.return_value
        with (
            patch("setup_repo.sync.get_repositories", return_value=repos_data),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=mock_sync_with_retries,
            ),
            patch("sys.exit"),
        ):
            sync_repositories(sample_config, dry_run=False)

        # クローン先ディレクトリが作成されたことを確認
        assert clone_destination.exists()

    def test_sync_with_existing_repositories(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
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

        repos_data = mock_github_api.get_user_repos.return_value
        with (
            patch("setup_repo.sync.get_repositories", return_value=repos_data),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                return_value=True,
            ),
            patch("sys.exit"),
        ):
            sync_repositories(sample_config, dry_run=False)

    def test_sync_dry_run_mode(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """ドライランモードでの同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        repos_data = mock_github_api.get_user_repos.return_value
        with (
            patch("setup_repo.sync.get_repositories", return_value=repos_data),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                return_value=True,
            ),
        ):
            sync_repositories(sample_config, dry_run=True)

    def test_sync_with_git_errors(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """Git操作エラー時の同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        repos_data = mock_github_api.get_user_repos.return_value
        with (
            patch("setup_repo.sync.get_repositories", return_value=repos_data),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                return_value=False,
            ),
            patch("sys.exit"),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        # エラーが適切に処理されることを確認
        # sync_repository_with_retriesがFalseを返しても、エラーは発生しない
        # 成功カウントが0になるだけ
        assert result.success  # エラーは発生しないので成功となる
        assert not result.synced_repos  # 同期されたリポジトリは0個

    def test_sync_with_network_errors(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
        mock_git_operations: Mock,
    ) -> None:
        """ネットワークエラー時の同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # GitHub APIでネットワークエラーをシミュレート
        mock_github_api_error = Mock()
        mock_github_api_error.get_user_repos.side_effect = Exception("ネットワークエラー")

        error = Exception("ネットワークエラー")
        with (
            patch("setup_repo.sync.get_repositories", side_effect=error),
            patch("sys.exit"),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert not result.success
        assert result.errors
        assert "ネットワークエラー" in str(result.errors[0])

    def test_sync_with_partial_failures(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """部分的な失敗がある同期テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        def mock_sync_side_effect(repo, dest_dir, config):
            # test-repo-1は成功、test-repo-2は失敗
            return "test-repo-1" in repo["name"]

        repos_data = mock_github_api.get_user_repos.return_value
        with (
            patch("setup_repo.sync.get_repositories", return_value=repos_data),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=mock_sync_side_effect,
            ),
            patch("sys.exit"),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert result.synced_repos

    @pytest.mark.slow
    def test_sync_performance_with_many_repositories(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
        mock_git_operations: Mock,
    ) -> None:
        """多数のリポジトリでの同期パフォーマンステスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 多数のリポジトリをシミュレート
        many_repos = [
            {
                "name": f"test-repo-{i}",
                "full_name": f"test_user/test-repo-{i}",
                "clone_url": f"https://github.com/test_user/test-repo-{i}.git",
                "ssh_url": f"git@github.com:test_user/test-repo-{i}.git",
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

        with (
            patch("setup_repo.sync.get_repositories", return_value=many_repos),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                return_value=True,
            ),
            patch("sys.exit"),
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
        sample_config: dict[str, Any],
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
                "full_name": "test_user/current-repo",
                "clone_url": "https://github.com/test_user/current-repo.git",
                "ssh_url": "git@github.com:test_user/current-repo.git",
                "description": "現在のリポジトリ",
                "private": False,
                "default_branch": "main",
            }
        ]
        mock_github_api.get_user_repos.return_value = current_repos

        with (
            patch("setup_repo.sync.get_repositories", return_value=current_repos),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                return_value=True,
            ),
            patch("sys.exit"),
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
        sample_config: dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
    ) -> None:
        """同期結果のシリアライゼーションテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        repos_data = mock_github_api.get_user_repos.return_value
        with (
            patch("setup_repo.sync.get_repositories", return_value=repos_data),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                return_value=True,
            ),
            patch("sys.exit"),
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
        assert json_str

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
            # 無効な設定では同期が失敗することを確認
            result = sync_repositories(invalid_config, dry_run=True)
            assert not result.success
            assert result.errors

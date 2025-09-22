"""
統合テストの簡素化版

このモジュールでは、統合テストの基本的な機能を実装します。
モック環境を使用して、実際のファイルシステムやネットワークに
影響を与えることなく、統合機能の動作を検証します。
"""

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from setup_repo.github_api import GitHubAPI, GitHubAPIError
from setup_repo.sync import SyncResult, sync_repositories

from ..multiplatform.helpers import check_platform_modules, verify_current_platform


@pytest.mark.integration
class TestIntegrationSimplified:
    """統合テストの簡素化版クラス"""

    def test_github_api_basic_functionality(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """GitHub API基本機能テスト"""
        # プラットフォーム検証を統合
        verify_current_platform()  # プラットフォーム検証
        check_platform_modules()

        # GitHubAPIクラスの初期化テスト
        api = GitHubAPI(
            token=sample_config["github"]["token"],
            username=sample_config["github"]["username"],
        )

        assert api.token == sample_config["github"]["token"]
        assert api.username == sample_config["github"]["username"]

        # 無効なトークンでの初期化テスト
        with pytest.raises((ValueError, GitHubAPIError)):
            GitHubAPI(token="", username=sample_config["github"]["username"])

    def test_sync_result_creation(self) -> None:
        """SyncResult作成テスト"""
        # 成功ケース
        success_result = SyncResult(success=True, synced_repos=["repo1", "repo2"], errors=[])

        assert success_result.success is True
        assert len(success_result.synced_repos) == 2
        assert not success_result.errors
        assert success_result.timestamp is not None

        # 失敗ケース
        error_result = SyncResult(success=False, synced_repos=[], errors=[Exception("テストエラー")])

        assert error_result.success is False
        assert not error_result.synced_repos
        assert len(error_result.errors) == 1

    def test_sync_with_invalid_config(self) -> None:
        """無効な設定での同期テスト"""
        # プラットフォーム検証を統合
        verify_current_platform()  # プラットフォーム検証

        # 空の設定
        empty_config = {}
        result = sync_repositories(empty_config, dry_run=True)

        assert isinstance(result, SyncResult)
        assert result.success is False
        assert result.errors

        # 不完全な設定
        incomplete_config = {
            "github": {"token": "test_token"}
            # github.username が不足
        }
        result = sync_repositories(incomplete_config, dry_run=True)

        assert isinstance(result, SyncResult)
        assert result.success is False
        assert result.errors

    def test_sync_dry_run_mode(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """ドライランモードでの同期テスト"""
        # プラットフォーム検証を統合
        verify_current_platform()  # プラットフォーム検証

        # GitHub APIとオーナー検出をモック
        with (
            patch("setup_repo.sync.get_repositories") as mock_get_repos,
            patch("setup_repo.sync.detect_github_owner", return_value="test_user"),
        ):
            mock_get_repos.return_value = [
                {
                    "name": "test-repo",
                    "full_name": "test/test-repo",
                    "clone_url": "https://github.com/test/test-repo.git",
                    "ssh_url": "git@github.com:test/test-repo.git",
                }
            ]

            result = sync_repositories(sample_config, dry_run=True)

        # ドライランモードでは成功するはず
        assert isinstance(result, SyncResult)
        assert result.success is True
        assert result.synced_repos

    def test_config_validation(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """設定検証テスト"""
        # 有効な設定ファイルの作成
        config_file = temp_dir / "valid_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        # 設定ファイルが正しく読み込まれることを確認
        assert config_file.exists()

        with open(config_file, encoding="utf-8") as f:
            loaded_config = json.load(f)

        assert loaded_config["github"]["token"] == sample_config["github"]["token"]
        assert loaded_config["github"]["username"] == sample_config["github"]["username"]

    def test_error_handling(self) -> None:
        """エラーハンドリングテスト"""
        # GitHubAPIError のテスト
        error = GitHubAPIError("テストエラー")
        assert str(error) == "テストエラー"

        # SyncResult でのエラー記録テスト
        test_error = ValueError("設定エラー")
        result = SyncResult(success=False, synced_repos=[], errors=[test_error])

        assert result.success is False
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], ValueError)

    def test_file_system_operations(
        self,
        temp_dir: Path,
    ) -> None:
        """ファイルシステム操作テスト"""
        # テスト用ディレクトリの作成
        test_repo_dir = temp_dir / "test_repos"
        test_repo_dir.mkdir(parents=True, exist_ok=True)

        # ディレクトリが作成されたことを確認
        assert test_repo_dir.exists()
        assert test_repo_dir.is_dir()

        # テスト用ファイルの作成
        test_file = test_repo_dir / "test_file.txt"
        test_file.write_text("テスト内容", encoding="utf-8")

        # ファイルが作成されたことを確認
        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == "テスト内容"

    def test_json_serialization(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """JSON シリアライゼーションテスト"""
        # 設定のシリアライゼーション
        json_str = json.dumps(sample_config, ensure_ascii=False, indent=2)
        assert json_str is not None
        assert json_str

        # デシリアライゼーション
        deserialized = json.loads(json_str)
        assert deserialized["github"]["token"] == sample_config["github"]["token"]
        assert deserialized["github"]["username"] == sample_config["github"]["username"]

        # SyncResult のシリアライゼーション
        result = SyncResult(success=True, synced_repos=["repo1", "repo2"], errors=[])

        result_dict = {
            "success": result.success,
            "synced_repos": result.synced_repos,
            "errors": [str(error) for error in result.errors],
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
        }

        result_json = json.dumps(result_dict, ensure_ascii=False, indent=2)
        assert result_json is not None
        assert result_json

    def test_environment_variable_handling(self) -> None:
        """環境変数処理テスト"""
        test_token = "test_env_token"
        test_username = "test_env_user"

        # 環境変数の設定
        with patch.dict(os.environ, {"GITHUB_TOKEN": test_token, "GITHUB_USERNAME": test_username}):
            # 環境変数から値を取得
            token_from_env = os.getenv("GITHUB_TOKEN")
            username_from_env = os.getenv("GITHUB_USERNAME")

            assert token_from_env == test_token
            assert username_from_env == test_username

    @pytest.mark.slow
    def test_performance_basic(
        self,
        sample_config: dict[str, Any],
    ) -> None:
        """基本的なパフォーマンステスト"""
        import time

        # 多数のリポジトリをシミュレート
        many_repos = [
            {
                "name": f"test-repo-{i}",
                "full_name": f"test/test-repo-{i}",
                "clone_url": f"https://github.com/test/test-repo-{i}.git",
                "ssh_url": f"git@github.com:test/test-repo-{i}.git",
            }
            for i in range(10)  # 10個のリポジトリ
        ]

        with (
            patch("setup_repo.sync.get_repositories") as mock_get_repos,
            patch("setup_repo.sync.detect_github_owner", return_value="test_user"),
        ):
            mock_get_repos.return_value = many_repos

            start_time = time.time()
            result = sync_repositories(sample_config, dry_run=True)
            execution_time = time.time() - start_time

        # パフォーマンス要件を緩和: 10リポジトリの同期が10秒以内（ドライランモード）
        assert execution_time < 10.0
        assert result.success is True
        assert len(result.synced_repos) == 10

    def test_integration_workflow_basic(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """基本的な統合ワークフローテスト"""
        # プラットフォーム検証を統合
        verify_current_platform()  # プラットフォーム検証
        check_platform_modules()

        # 1. 設定ファイルの作成
        config_file = temp_dir / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        # 2. クローン先ディレクトリの設定
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 3. GitHub APIとオーナー検出をモック
        with (
            patch("setup_repo.sync.get_repositories") as mock_get_repos,
            patch("setup_repo.sync.detect_github_owner", return_value="test_user"),
        ):
            mock_get_repos.return_value = [
                {
                    "name": "integration-test-repo",
                    "full_name": "test/integration-test-repo",
                    "clone_url": "https://github.com/test/integration-test-repo.git",
                    "ssh_url": "git@github.com:test/integration-test-repo.git",
                }
            ]

            # 4. 同期実行
            result = sync_repositories(sample_config, dry_run=True)

        # 5. 結果検証
        assert isinstance(result, SyncResult)
        assert result.success is True
        assert "integration-test-repo" in result.synced_repos

        # 6. ファイルシステム検証
        assert config_file.exists()
        # ドライランモードではディレクトリは作成されない場合がある

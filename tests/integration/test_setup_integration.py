"""
setup機能の統合テスト

このモジュールでは、setup機能全体の統合テストを実装します。
モック環境を使用して、実際のファイルシステムやネットワークに
影響を与えることなく、setup機能の動作を検証します。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from setup_repo.config import load_config
from setup_repo.interactive_setup import InteractiveSetup
from setup_repo.setup import setup_repository_environment


@pytest.mark.integration
class TestSetupIntegration:
    """setup機能の統合テストクラス"""

    def test_complete_setup_workflow_with_mocks(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
        mock_platform_detector: Mock,
        mock_subprocess: Mock,
    ) -> None:
        """完全なセットアップワークフローのテスト（モック環境）"""
        # テスト用設定ファイルを作成
        config_file = temp_dir / "config.local.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        # 環境変数を設定
        with patch.dict(os.environ, {"CONFIG_PATH": str(config_file)}):
            # モックを適用してsetup機能を実行
            with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
                with patch(
                    "setup_repo.git_operations.GitOperations",
                    return_value=mock_git_operations,
                ):
                    with patch(
                        "setup_repo.platform_detector.PlatformDetector",
                        return_value=mock_platform_detector,
                    ):
                        # setup機能を実行
                        result = setup_repository_environment(
                            config_path=str(config_file), dry_run=True
                        )

        # 結果を検証
        assert result is not None
        assert isinstance(result, dict)

        # モックが適切に呼び出されたことを確認
        mock_platform_detector.detect_platform.assert_called()
        mock_github_api.get_user_info.assert_called()

    def test_interactive_setup_workflow(
        self,
        temp_dir: Path,
        mock_github_api: Mock,
        mock_platform_detector: Mock,
    ) -> None:
        """インタラクティブセットアップワークフローのテスト"""
        # テスト用の入力データを準備
        test_inputs = {
            "github_token": "test_interactive_token",
            "github_username": "test_interactive_user",
            "clone_destination": str(temp_dir / "repos"),
            "auto_install_dependencies": True,
            "setup_vscode": True,
        }

        # インタラクティブセットアップのインスタンスを作成
        interactive_setup = InteractiveSetup()

        # モックを適用してインタラクティブセットアップを実行
        with patch("builtins.input") as mock_input:
            # 入力値を順番に設定
            mock_input.side_effect = [
                test_inputs["github_token"],
                test_inputs["github_username"],
                test_inputs["clone_destination"],
                "y",  # auto_install_dependencies
                "y",  # setup_vscode
                "y",  # 設定を保存するか
            ]

            with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
                with patch(
                    "setup_repo.platform_detector.PlatformDetector",
                    return_value=mock_platform_detector,
                ):
                    # インタラクティブセットアップを実行
                    config = interactive_setup.run_setup()

        # 結果を検証
        assert config is not None
        assert config["github_token"] == test_inputs["github_token"]
        assert config["github_username"] == test_inputs["github_username"]
        assert config["clone_destination"] == test_inputs["clone_destination"]
        assert config["auto_install_dependencies"] is True
        assert config["setup_vscode"] is True

    def test_setup_with_invalid_config(
        self,
        temp_dir: Path,
        mock_github_api: Mock,
    ) -> None:
        """無効な設定でのセットアップテスト"""
        # 無効な設定を作成（必須フィールドが不足）
        invalid_config = {
            "github_token": "",  # 空のトークン
            "clone_destination": str(temp_dir / "repos"),
        }

        config_file = temp_dir / "invalid_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(invalid_config, f, indent=2, ensure_ascii=False)

        # 無効な設定でのセットアップ実行
        with patch.dict(os.environ, {"CONFIG_PATH": str(config_file)}):
            with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
                # エラーが発生することを確認
                with pytest.raises((ValueError, KeyError)):
                    setup_repository_environment(
                        config_path=str(config_file), dry_run=True
                    )

    def test_setup_with_github_api_error(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_platform_detector: Mock,
    ) -> None:
        """GitHub API エラー時のセットアップテスト"""
        # GitHub APIエラーをシミュレート
        mock_github_api_error = Mock()
        mock_github_api_error.get_user_info.side_effect = Exception("GitHub API エラー")

        config_file = temp_dir / "config.local.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        # GitHub APIエラー時のセットアップ実行
        with patch.dict(os.environ, {"CONFIG_PATH": str(config_file)}):
            with patch(
                "setup_repo.github_api.GitHubAPI", return_value=mock_github_api_error
            ):
                with patch(
                    "setup_repo.platform_detector.PlatformDetector",
                    return_value=mock_platform_detector,
                ):
                    # エラーハンドリングが適切に行われることを確認
                    with pytest.raises(Exception):
                        setup_repository_environment(
                            config_path=str(config_file), dry_run=False
                        )

    def test_setup_dry_run_mode(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_git_operations: Mock,
        mock_platform_detector: Mock,
    ) -> None:
        """ドライランモードでのセットアップテスト"""
        config_file = temp_dir / "config.local.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        # ドライランモードでセットアップを実行
        with patch.dict(os.environ, {"CONFIG_PATH": str(config_file)}):
            with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
                with patch(
                    "setup_repo.git_operations.GitOperations",
                    return_value=mock_git_operations,
                ):
                    with patch(
                        "setup_repo.platform_detector.PlatformDetector",
                        return_value=mock_platform_detector,
                    ):
                        result = setup_repository_environment(
                            config_path=str(config_file), dry_run=True
                        )

        # ドライランモードでは実際の変更が行われないことを確認
        assert result is not None

        # 実際のファイル操作が行われていないことを確認
        # （ドライランモードでは、実際のクローンやファイル作成は行われない）
        repos_dir = Path(sample_config["clone_destination"])
        if repos_dir.exists():
            # ドライランモードでは新しいリポジトリは作成されない
            existing_repos = list(repos_dir.iterdir())
            # テスト環境では既存のリポジトリのみが存在する
            assert len(existing_repos) == 0 or all(
                repo.name.startswith("test-") for repo in existing_repos
            )

    @pytest.mark.slow
    def test_setup_with_file_system_operations(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
        mock_github_api: Mock,
        mock_platform_detector: Mock,
    ) -> None:
        """ファイルシステム操作を含むセットアップテスト"""
        # テスト用のクローン先ディレクトリを設定
        clone_destination = temp_dir / "test_repos"
        sample_config["clone_destination"] = str(clone_destination)

        config_file = temp_dir / "config.local.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        # 実際のファイルシステム操作を含むセットアップを実行
        with patch.dict(os.environ, {"CONFIG_PATH": str(config_file)}):
            with patch("setup_repo.github_api.GitHubAPI", return_value=mock_github_api):
                with patch(
                    "setup_repo.platform_detector.PlatformDetector",
                    return_value=mock_platform_detector,
                ):
                    # Git操作は実際には行わず、ディレクトリ作成のみテスト
                    with patch("setup_repo.git_operations.GitOperations") as mock_git:
                        mock_git.return_value.clone_repository.return_value = True

                        result = setup_repository_environment(
                            config_path=str(config_file), dry_run=False
                        )

        # 結果を検証
        assert result is not None

        # クローン先ディレクトリが作成されたことを確認
        assert clone_destination.exists()
        assert clone_destination.is_dir()

    def test_config_loading_integration(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
    ) -> None:
        """設定読み込みの統合テスト"""
        # 複数の設定ファイルを作成してテスト
        config_files = {
            "config.json": {
                "github_token": "default_token",
                "github_username": "default_user",
                "clone_destination": "/default/path",
            },
            "config.local.json": sample_config,
        }

        for filename, config_data in config_files.items():
            config_file = temp_dir / filename
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

        # 設定読み込みをテスト
        with patch.dict(os.environ, {"CONFIG_PATH": str(temp_dir)}):
            loaded_config = load_config()

        # local設定が優先されることを確認
        assert loaded_config["github_token"] == sample_config["github_token"]
        assert loaded_config["github_username"] == sample_config["github_username"]
        assert loaded_config["clone_destination"] == sample_config["clone_destination"]

    def test_environment_variable_override(
        self,
        temp_dir: Path,
        sample_config: Dict[str, Any],
    ) -> None:
        """環境変数による設定上書きのテスト"""
        config_file = temp_dir / "config.local.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        # 環境変数で設定を上書き
        env_overrides = {
            "CONFIG_PATH": str(config_file),
            "GITHUB_TOKEN": "env_override_token",
            "GITHUB_USERNAME": "env_override_user",
        }

        with patch.dict(os.environ, env_overrides):
            loaded_config = load_config()

        # 環境変数による上書きが適用されることを確認
        assert loaded_config["github_token"] == "env_override_token"
        assert loaded_config["github_username"] == "env_override_user"
        # ファイルからの設定も保持されることを確認
        assert loaded_config["clone_destination"] == sample_config["clone_destination"]

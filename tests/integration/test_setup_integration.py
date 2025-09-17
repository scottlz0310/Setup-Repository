"""
setup機能の統合テスト

ルールに従い、プラットフォーム依存のテストは実環境で実行し、
外部依存（GitHub API等）のみモックを使用します。
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.setup_repo.setup import setup_repository_environment


@pytest.mark.integration
class TestSetupIntegration:
    """setup機能の統合テストクラス（実環境重視）"""

    @pytest.mark.slow
    def test_setup_with_file_system_operations(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
        mock_github_api: Mock,
    ) -> None:
        """ファイルシステム操作を含むセットアップテスト（実環境）"""
        clone_destination = temp_dir / "test_repos"
        sample_config["clone_destination"] = str(clone_destination)

        config_file = temp_dir / "config.local.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        # 外部依存（GitHub API）のみモック、プラットフォーム検出は実環境
        with patch("src.setup_repo.setup.GitHubAPI", return_value=mock_github_api):
            result = setup_repository_environment(config_path=str(config_file), dry_run=False)

        assert result is not None
        assert clone_destination.exists()
        assert clone_destination.is_dir()

    def test_setup_with_invalid_config(
        self,
        temp_dir: Path,
    ) -> None:
        """無効な設定でのセットアップテスト（実環境）"""
        invalid_config = {
            "github_token": "",
            "clone_destination": str(temp_dir / "repos"),
        }

        config_file = temp_dir / "invalid_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(invalid_config, f, indent=2, ensure_ascii=False)

        with pytest.raises(ValueError, match="必須フィールドが不足しています"):
            setup_repository_environment(config_path=str(config_file), dry_run=True)

    def test_setup_with_github_api_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """GitHub API エラー時のセットアップテスト（実環境）"""
        mock_github_api_error = Mock()
        mock_github_api_error.get_user_info.side_effect = Exception("GitHub API エラー")

        config_file = temp_dir / "config.local.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        with (
            patch("src.setup_repo.setup.GitHubAPI", return_value=mock_github_api_error),
            pytest.raises(Exception, match="GitHub API エラー"),
        ):
            setup_repository_environment(config_path=str(config_file), dry_run=False)

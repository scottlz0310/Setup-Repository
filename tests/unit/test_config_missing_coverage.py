"""config.pyの未テスト部分のテスト"""

import json
import os
from unittest.mock import patch

import pytest

from src.setup_repo.config import get_github_token, load_config

from ..multiplatform.helpers import verify_current_platform


class TestConfigMissingCoverage:
    """config.pyの未テスト部分のテストクラス"""

    @pytest.mark.unit
    def test_get_github_token_gh_cli_failure(self):
        """gh CLI失敗時のテスト（20行）"""
        verify_current_platform()

        # 環境変数をクリア
        with (
            patch.dict(os.environ, {}, clear=True),
            # gh CLIが失敗する場合をテスト
            patch("subprocess.run", side_effect=FileNotFoundError("gh command not found")),
        ):
                token = get_github_token()
                assert token is None  # 20行のreturn Noneをテスト

    @pytest.mark.unit
    def test_load_config_direct_file_path(self, temp_dir):
        """CONFIG_PATHが直接ファイルを指す場合のテスト（78行）"""
        verify_current_platform()

        # テスト用設定ファイルを作成
        config_file = temp_dir / "config.local.json"
        test_config = {"owner": "direct_file_test", "dest": "/test/path"}

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(test_config, f)

        # CONFIG_PATHが直接ファイルを指す場合
        with patch.dict(os.environ, {"CONFIG_PATH": str(config_file)}):
            config = load_config()

            # 78行のconfig_path = config_dirが実行されることを確認
            assert config["owner"] == "direct_file_test"
            assert config["dest"] == "/test/path"

    @pytest.mark.unit
    def test_load_config_mismatched_file_path(self, temp_dir):
        """CONFIG_PATHとファイル名が一致しない場合のテスト"""
        verify_current_platform()

        # テスト用設定ファイルを作成
        config_file = temp_dir / "config.local.json"
        test_config = {"owner": "mismatch_test", "dest": "/mismatch/path"}

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(test_config, f)

        # CONFIG_PATHが異なるファイル名を指す場合
        different_file = temp_dir / "different.json"
        with patch.dict(os.environ, {"CONFIG_PATH": str(different_file)}):
            config = load_config()

            # ファイルが見つからないため、自動検出設定が使用される
            assert config["owner"] != "mismatch_test"  # ファイル設定は読み込まれない

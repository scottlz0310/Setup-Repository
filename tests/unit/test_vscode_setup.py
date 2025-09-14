"""
VS Code設定機能のテスト

マルチプラットフォームテスト方針に準拠したVS Code設定機能のテスト
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from setup_repo.vscode_setup import (
    apply_vscode_template,
)
from tests.multiplatform.helpers import (
    get_platform_specific_config,
    verify_current_platform,
)


class TestVscodeSetup:
    """VS Code設定機能のテスト"""

    def test_apply_vscode_template_success(self):
        """VS Codeテンプレート適用成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # テンプレートディレクトリを作成
            template_dir = repo_path / "vscode-templates" / "linux"
            template_dir.mkdir(parents=True)

            # テンプレートファイルを作成
            settings_file = template_dir / "settings.json"
            settings_file.write_text('{"python.defaultInterpreter": "python"}')

            with patch("setup_repo.vscode_setup.__file__", str(repo_path / "vscode_setup.py")), patch("builtins.print"):
                result = apply_vscode_template(repo_path, "linux", dry_run=False)

                # テンプレートがない場合はTrueを返す
                assert result is True

    def test_apply_vscode_template_dry_run(self):
        """VS Codeテンプレートドライランテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("builtins.print"):
                result = apply_vscode_template(repo_path, "linux", dry_run=True)
                assert result is True

    def test_apply_vscode_template_no_template(self):
        """テンプレートがない場合のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("setup_repo.vscode_setup.__file__", str(repo_path / "vscode_setup.py")), patch("builtins.print"):
                result = apply_vscode_template(repo_path, "nonexistent", dry_run=False)
                assert result is True  # テンプレートがない場合はスキップ

    def test_apply_vscode_template_with_backup(self):
        """既存設定のバックアップテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # 既存の.vscodeディレクトリを作成
            existing_vscode = repo_path / ".vscode"
            existing_vscode.mkdir()
            (existing_vscode / "settings.json").write_text('{"old": "setting"}')

            # テンプレートディレクトリを作成
            template_dir = repo_path / "vscode-templates" / "linux"
            template_dir.mkdir(parents=True)
            (template_dir / "settings.json").write_text('{"new": "setting"}')

            with (
                patch("setup_repo.vscode_setup.__file__", str(repo_path / "vscode_setup.py")),
                patch("builtins.print"),
                patch("time.time", return_value=1234567890),
            ):
                result = apply_vscode_template(repo_path, "linux", dry_run=False)
                assert result is True

                # バックアップファイルが作成されたことを確認
                backup_dir = repo_path / ".vscode.bak.1234567890"
                assert backup_dir.exists()

    def test_apply_vscode_template_error_handling(self):
        """VS Codeテンプレート適用エラーハンドリングテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # テンプレートディレクトリを作成
            template_dir = repo_path / "vscode-templates" / "linux"
            template_dir.mkdir(parents=True)
            (template_dir / "settings.json").write_text('{"test": "setting"}')

            with (
                patch("setup_repo.vscode_setup.__file__", str(repo_path / "vscode_setup.py")),
                patch("builtins.print"),
                patch("shutil.copytree") as mock_copytree,
            ):
                mock_copytree.side_effect = Exception("コピーエラー")

                result = apply_vscode_template(repo_path, "linux", dry_run=False)
                assert result is False

    @pytest.mark.integration
    def test_apply_vscode_template_integration(self):
        """VS Codeテンプレート適用統合テスト"""
        platform_info = verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # プラットフォーム固有のテンプレートディレクトリを作成
            platform_name = "windows" if platform_info.name == "windows" else "linux"
            template_dir = repo_path / "vscode-templates" / platform_name
            template_dir.mkdir(parents=True)

            # プラットフォーム固有の設定を作成
            settings = {"python.defaultInterpreter": "python", "editor.formatOnSave": True}
            (template_dir / "settings.json").write_text(json.dumps(settings, indent=2))

            with patch("setup_repo.vscode_setup.__file__", str(repo_path / "vscode_setup.py")), patch("builtins.print"):
                result = apply_vscode_template(repo_path, platform_name, dry_run=False)
                assert result is True

                # 設定が適用されたことを確認
                vscode_settings = repo_path / ".vscode" / "settings.json"
                assert vscode_settings.exists()

                with open(vscode_settings, encoding="utf-8") as f:
                    applied_settings = json.load(f)
                    assert applied_settings["python.defaultInterpreter"] == "python"
                    assert applied_settings["editor.formatOnSave"] is True

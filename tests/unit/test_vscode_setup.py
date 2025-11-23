"""
VS Code設定機能のテスト

マルチプラットフォームテスト方針に準拠したVS Code設定機能のテスト
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from setup_repo.vscode_setup import apply_vscode_template
from tests.multiplatform.helpers import get_platform_specific_config, verify_current_platform


class TestVscodeSetup:
    """VS Code設定機能のテスト"""

    def test_apply_vscode_template_success(self):
        """VS Codeテンプレート適用成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # 実際のパッケージテンプレートを使用
            with patch("builtins.print"):
                result = apply_vscode_template(repo_path, "linux", dry_run=False)
                # パッケージテンプレートがあるので成功するはず
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

    def test_apply_vscode_template_with_merge(self):
        """既存設定のマージテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Pythonプロジェクトとして認識させる
            (repo_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

            # 既存の.vscodeディレクトリを作成
            existing_vscode = repo_path / ".vscode"
            existing_vscode.mkdir()
            existing_settings = {"custom": "setting", "editor.fontSize": 14}
            (existing_vscode / "settings.json").write_text(json.dumps(existing_settings))

            # 実際のパッケージテンプレートを使用
            with patch("builtins.print"):
                result = apply_vscode_template(repo_path, "linux", dry_run=False)
                assert result is True

                # 既存設定がマージされていることを確認
                settings_file = repo_path / ".vscode" / "settings.json"
                assert settings_file.exists()

                merged_settings = json.loads(settings_file.read_text())
                # 既存設定が保持されている
                assert merged_settings.get("custom") == "setting"
                assert merged_settings.get("editor.fontSize") == 14
                # テンプレート設定も追加されている
                assert "editor.formatOnSave" in merged_settings

    def test_apply_vscode_template_with_invalid_json_backup(self):
        """無効なJSON設定のバックアップテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Pythonプロジェクトとして認識させる
            (repo_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

            # 既存の.vscodeディレクトリに無効なJSONを作成
            existing_vscode = repo_path / ".vscode"
            existing_vscode.mkdir()
            (existing_vscode / "settings.json").write_text('{"invalid json')

            # 実際のパッケージテンプレートを使用
            with (
                patch("builtins.print"),
                patch("time.time", return_value=1234567890),
            ):
                result = apply_vscode_template(repo_path, "linux", dry_run=False)
                assert result is True

                # 無効なJSONの場合はバックアップが作成される
                backup_dir = repo_path / ".vscode.bak.1234567890"
                assert backup_dir.exists()

    def test_apply_vscode_template_error_handling(self):
        """VS Codeテンプレート適用エラーハンドリングテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # 実際のパッケージテンプレートを使用し、エラーを発生させる
            with (
                patch("builtins.print"),
                patch("pathlib.Path.mkdir") as mock_mkdir,
            ):
                mock_mkdir.side_effect = Exception("ディレクトリ作成エラー")

                result = apply_vscode_template(repo_path, "linux", dry_run=False)
                assert result is False

    @pytest.mark.integration
    def test_apply_vscode_template_integration(self):
        """VS Codeテンプレート適用統合テスト"""
        platform_info = verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Pythonプロジェクトとして認識させる
            (repo_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

            # プラットフォーム固有のテンプレートディレクトリを作成
            # 実際のパッケージテンプレートを使用するため、ダミーは不要
            platform_name = "windows" if platform_info.name == "windows" else "linux"

            with patch("builtins.print"):
                result = apply_vscode_template(repo_path, platform_name, dry_run=False)
                # 実際のパッケージテンプレートがあるので成功するはず
                assert result is True

                # 設定が適用されたことを確認
                vscode_settings = repo_path / ".vscode" / "settings.json"
                if vscode_settings.exists():
                    # パッケージから実際にマージされた場合
                    with open(vscode_settings, encoding="utf-8") as f:
                        applied_settings = json.load(f)
                        # common設定が含まれているか
                        assert "editor.formatOnSave" in applied_settings
                        # python関連の設定も含まれているか
                        assert "python.terminal.activateEnvironment" in applied_settings
                        # プラットフォーム固有の設定も含まれているか
                        assert (
                            "files.eol" in applied_settings
                            or "terminal.integrated.defaultProfile.windows" in applied_settings
                        )

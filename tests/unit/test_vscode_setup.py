"""
VS Code設定機能のテスト

マルチプラットフォームテスト方針に準拠したVS Code設定機能のテスト
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.vscode_setup import (
    VscodeSetup,
    VscodeSetupError,
    create_vscode_settings,
    get_vscode_settings_path,
    install_vscode_extensions,
    setup_vscode_config,
)
from tests.multiplatform.helpers import (
    get_platform_specific_config,
    skip_if_not_platform,
    verify_current_platform,
)


class TestVscodeSetup:
    """VS Code設定機能のテスト"""

    def test_get_vscode_settings_path_project(self):
        """プロジェクト内のVS Code設定パス取得テスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            settings_path = get_vscode_settings_path(project_path)

            expected_path = project_path / ".vscode" / "settings.json"
            assert settings_path == expected_path

    @pytest.mark.windows
    def test_get_vscode_settings_path_global_windows(self):
        """Windows環境でのグローバルVS Code設定パス取得テスト"""
        skip_if_not_platform("windows")

        with patch.dict("os.environ", {"APPDATA": "C:\\Users\\test\\AppData\\Roaming"}):
            settings_path = get_vscode_settings_path(global_settings=True)

            expected = Path("C:\\Users\\test\\AppData\\Roaming\\Code\\User\\settings.json")
            assert settings_path == expected

    @pytest.mark.unix
    def test_get_vscode_settings_path_global_unix(self):
        """Unix系環境でのグローバルVS Code設定パス取得テスト"""
        skip_if_not_platform("unix")

        with patch.dict("os.environ", {"HOME": "/home/test"}):
            settings_path = get_vscode_settings_path(global_settings=True)

            expected = Path("/home/test/.config/Code/User/settings.json")
            assert settings_path == expected

    @pytest.mark.macos
    def test_get_vscode_settings_path_global_macos(self):
        """macOS環境でのグローバルVS Code設定パス取得テスト"""
        skip_if_not_platform("macos")

        with patch.dict("os.environ", {"HOME": "/Users/test"}):
            settings_path = get_vscode_settings_path(global_settings=True)

            expected = Path("/Users/test/Library/Application Support/Code/User/settings.json")
            assert settings_path == expected

    def test_create_vscode_settings_new_file(self):
        """新規VS Code設定ファイル作成テスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / ".vscode" / "settings.json"

            settings = {"python.defaultInterpreter": "python", "editor.formatOnSave": True}

            result = create_vscode_settings(settings_path, settings)

            assert result["created"] is True
            assert settings_path.exists()

            # 作成された設定を確認
            with open(settings_path, encoding="utf-8") as f:
                saved_settings = json.load(f)

            assert saved_settings["python.defaultInterpreter"] == "python"
            assert saved_settings["editor.formatOnSave"] is True

    def test_create_vscode_settings_merge_existing(self):
        """既存VS Code設定ファイルとのマージテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vscode_dir = Path(temp_dir) / ".vscode"
            vscode_dir.mkdir()
            settings_path = vscode_dir / "settings.json"

            # 既存設定を作成
            existing_settings = {"editor.tabSize": 4, "python.defaultInterpreter": "old_python"}
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(existing_settings, f)

            # 新しい設定をマージ
            new_settings = {"python.defaultInterpreter": "new_python", "editor.formatOnSave": True}

            result = create_vscode_settings(settings_path, new_settings)

            assert result["merged"] is True

            # マージされた設定を確認
            with open(settings_path, encoding="utf-8") as f:
                merged_settings = json.load(f)

            assert merged_settings["editor.tabSize"] == 4  # 既存設定が保持
            assert merged_settings["python.defaultInterpreter"] == "new_python"  # 新設定で上書き
            assert merged_settings["editor.formatOnSave"] is True  # 新設定が追加

    def test_create_vscode_settings_invalid_json(self):
        """無効なJSON設定ファイルの処理テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vscode_dir = Path(temp_dir) / ".vscode"
            vscode_dir.mkdir()
            settings_path = vscode_dir / "settings.json"

            # 無効なJSONファイルを作成
            with open(settings_path, "w", encoding="utf-8") as f:
                f.write('{"invalid": json}')

            new_settings = {"editor.formatOnSave": True}

            with pytest.raises(VscodeSetupError, match="無効なJSON"):
                create_vscode_settings(settings_path, new_settings)

    def test_install_vscode_extensions_success(self):
        """VS Code拡張機能インストール成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        extensions = ["ms-python.python", "charliermarsh.ruff", "ms-python.mypy-type-checker"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Extension installed")

            result = install_vscode_extensions(extensions)

            assert result["success"] is True
            assert len(result["installed"]) == 3
            assert "ms-python.python" in result["installed"]

    def test_install_vscode_extensions_partial_failure(self):
        """VS Code拡張機能の部分的インストール失敗テスト"""
        extensions = ["ms-python.python", "invalid-extension"]

        with patch("subprocess.run") as mock_run:
            # 最初の拡張機能は成功、2番目は失敗
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Extension installed"),
                Mock(returncode=1, stderr="Extension not found"),
            ]

            result = install_vscode_extensions(extensions)

            assert result["success"] is False
            assert len(result["installed"]) == 1
            assert len(result["failed"]) == 1
            assert "ms-python.python" in result["installed"]
            assert "invalid-extension" in result["failed"]

    def test_install_vscode_extensions_code_not_found(self):
        """VS Codeが見つからない場合のテスト"""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None

            with pytest.raises(VscodeSetupError, match="VS Codeが見つかりません"):
                install_vscode_extensions(["ms-python.python"])

    def test_vscode_setup_init(self):
        """VscodeSetupクラスの初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            setup = VscodeSetup(temp_dir)

            assert setup.project_path == Path(temp_dir)
            assert setup.platform == platform_info.name

    def test_vscode_setup_configure_project(self):
        """プロジェクト設定の構成テスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            setup = VscodeSetup(temp_dir)

            result = setup.configure_project()

            assert result["success"] is True
            assert result["settings_created"] is True

            # 設定ファイルが作成されたことを確認
            settings_path = Path(temp_dir) / ".vscode" / "settings.json"
            assert settings_path.exists()

    def test_vscode_setup_configure_with_custom_settings(self):
        """カスタム設定での構成テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = VscodeSetup(temp_dir)

            custom_settings = {"python.defaultInterpreter": "/usr/bin/python3", "editor.rulers": [88, 120]}

            result = setup.configure_project(custom_settings)

            assert result["success"] is True

            # カスタム設定が適用されたことを確認
            settings_path = Path(temp_dir) / ".vscode" / "settings.json"
            with open(settings_path, encoding="utf-8") as f:
                saved_settings = json.load(f)

            assert saved_settings["python.defaultInterpreter"] == "/usr/bin/python3"
            assert saved_settings["editor.rulers"] == [88, 120]

    @pytest.mark.integration
    def test_full_vscode_setup_workflow(self):
        """完全なVS Codeセットアップワークフローのテスト"""
        verify_current_platform()  # プラットフォーム検証

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("subprocess.run") as mock_run,
            patch("shutil.which") as mock_which,
        ):
            # VS Codeが利用可能
            mock_which.return_value = "/usr/bin/code"

            # 拡張機能インストールが成功
            mock_run.return_value = Mock(returncode=0, stdout="Success")

            result = setup_vscode_config(project_path=temp_dir, install_extensions=True)

            assert result["success"] is True
            assert result["settings_configured"] is True
            assert result["extensions_installed"] is True

    @pytest.mark.slow
    def test_vscode_setup_performance(self):
        """VS Codeセットアップのパフォーマンステスト"""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            start_time = time.time()

            setup = VscodeSetup(temp_dir)

            # 複数回設定を実行してパフォーマンスを測定
            for _ in range(5):
                setup.configure_project()

            elapsed = time.time() - start_time
            assert elapsed < 2.0, f"VS Code設定が遅すぎます: {elapsed}秒"

    def test_vscode_setup_error_handling(self):
        """VS Codeセットアップのエラーハンドリングテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = VscodeSetup(temp_dir)

            # 読み取り専用ディレクトリでの設定試行
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                mock_mkdir.side_effect = PermissionError("Permission denied")

                with pytest.raises(VscodeSetupError, match="権限エラー"):
                    setup.configure_project()

    def test_platform_specific_settings(self):
        """プラットフォーム固有設定のテスト"""
        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        with tempfile.TemporaryDirectory() as temp_dir:
            setup = VscodeSetup(temp_dir)

            # プラットフォーム固有の設定を適用
            result = setup.configure_project(platform_optimized=True)

            assert result["success"] is True

            # プラットフォーム固有設定が適用されたことを確認
            settings_path = Path(temp_dir) / ".vscode" / "settings.json"
            with open(settings_path, encoding="utf-8") as f:
                settings = json.load(f)

            # プラットフォームに応じた設定が含まれることを確認
            if platform_info.name == "windows":
                assert "terminal.integrated.shell.windows" in settings
            else:
                assert "terminal.integrated.shell.linux" in settings or "terminal.integrated.shell.osx" in settings

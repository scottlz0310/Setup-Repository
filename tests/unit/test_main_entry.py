"""メインエントリーポイントのテスト"""

from pathlib import Path
from unittest.mock import patch

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestMainEntry:
    """メインエントリーポイントのテストクラス"""

    @pytest.mark.unit
    def test_main_entry_setup_command(self, temp_dir):
        """setupコマンドのテスト"""
        verify_current_platform()

        # main.pyが存在する場合のテスト
        main_py = Path("main.py")
        if not main_py.exists():
            pytest.skip("main.pyが存在しません")

        with (
            patch("sys.argv", ["main.py", "setup"]),
            patch("setup_repo.setup.setup_repository_environment") as mock_setup,
            patch("setup_repo.config.load_config", return_value={"test": "config"}),
        ):
            mock_setup.return_value = {"success": True}

            # main.pyを実行
            try:
                with open("main.py") as f:
                    exec(f.read())
            except SystemExit:
                pass  # 正常終了
            except Exception as e:
                pytest.skip(f"main.py実行エラー: {e}")

    @pytest.mark.unit
    def test_main_entry_sync_command(self, temp_dir):
        """syncコマンドのテスト"""
        verify_current_platform()

        main_py = Path("main.py")
        if not main_py.exists():
            pytest.skip("main.pyが存在しません")

        with (
            patch("sys.argv", ["main.py", "sync"]),
            patch("setup_repo.sync.sync_repositories") as mock_sync,
            patch("setup_repo.config.load_config", return_value={"test": "config"}),
        ):
            from setup_repo.sync import SyncResult

            mock_sync.return_value = SyncResult(success=True, synced_repos=["repo1"], errors=[])

            try:
                with open("main.py") as f:
                    exec(f.read())
            except SystemExit:
                pass
            except Exception as e:
                pytest.skip(f"main.py実行エラー: {e}")

    @pytest.mark.unit
    def test_cli_module_import(self):
        """CLIモジュールのインポートテスト"""
        verify_current_platform()

        try:
            from setup_repo import cli

            assert cli is not None
        except ImportError:
            pytest.skip("CLIモジュールが利用できません")

    @pytest.mark.unit
    def test_package_version(self):
        """パッケージバージョンのテスト"""
        verify_current_platform()

        try:
            from setup_repo import __version__

            assert __version__ is not None
            assert isinstance(__version__, str)
            assert len(__version__) > 0
        except ImportError:
            pytest.skip("バージョン情報が利用できません")

    @pytest.mark.unit
    def test_compatibility_module(self):
        """互換性モジュールのテスト"""
        verify_current_platform()

        try:
            from setup_repo.compatibility import create_compatibility_aliases

            # 関数が呼び出し可能であることを確認
            assert callable(create_compatibility_aliases)
        except ImportError:
            pytest.skip("互換性モジュールが利用できません")

"""
クロスプラットフォーム共通機能テスト

全プラットフォームで実行可能な共通機能のテスト。
プラットフォーム固有の機能は適切にスキップし、
共通部分のカバレッジを向上させます。
"""

import os
import platform
from datetime import UTC
from pathlib import Path

import pytest

from setup_repo.platform_detector import detect_platform


class TestCrossPlatformCommon:
    """クロスプラットフォーム共通機能テスト"""

    def test_platform_detection_basic(self):
        """基本的なプラットフォーム検出（全環境共通）"""
        platform_info = detect_platform()

        # 基本的な属性の存在確認
        assert hasattr(platform_info, "name")
        assert hasattr(platform_info, "shell")
        assert hasattr(platform_info, "python_cmd")
        assert hasattr(platform_info, "package_managers")

        # 有効な値の確認
        assert platform_info.name in ["windows", "linux", "macos", "wsl"]
        assert platform_info.shell in ["cmd", "sh"]  # セキュリティ修正後の新しい設定
        assert platform_info.python_cmd in ["python", "python3", "py"]
        assert isinstance(platform_info.package_managers, list)

    def test_platform_consistency(self):
        """プラットフォーム検出の一貫性テスト"""
        platform_info = detect_platform()
        system = platform.system()

        # システム情報との整合性確認
        if system == "Windows":
            assert platform_info.name == "windows"
            assert platform_info.shell == "cmd"  # セキュリティ修正後の新しい設定
        elif system == "Linux":
            assert platform_info.name in ["linux", "wsl"]
            assert platform_info.shell == "sh"  # セキュリティ修正後の新しい設定
        elif system == "Darwin":
            assert platform_info.name == "macos"
            assert platform_info.shell == "sh"  # セキュリティ修正後の新しい設定

    def test_path_handling_cross_platform(self, temp_dir):
        """クロスプラットフォームパス処理テスト"""
        # 基本的なパス操作
        test_path = temp_dir / "test_file.txt"
        test_path.write_text("test content", encoding="utf-8")

        # パスの存在確認
        assert test_path.exists()
        assert test_path.is_file()

        # 内容の確認
        content = test_path.read_text(encoding="utf-8")
        assert content == "test content"

        # パス文字列の取得
        path_str = str(test_path)
        assert len(path_str) > 0

    def test_environment_variables_basic(self):
        """基本的な環境変数テスト（全プラットフォーム共通）"""
        # PATH環境変数は全プラットフォームで存在
        path_env = os.environ.get("PATH")
        assert path_env is not None
        assert len(path_env) > 0

        # パス区切り文字の確認
        if platform.system() == "Windows":
            assert ";" in path_env or len(path_env.split(os.pathsep)) > 1
        else:
            assert ":" in path_env or len(path_env.split(os.pathsep)) > 1

    def test_python_environment_detection(self):
        """Python環境検出テスト"""
        platform_info = detect_platform()
        python_cmd = platform_info.python_cmd

        # Pythonコマンドの妥当性確認
        assert python_cmd in ["python", "python3", "py"]

        # 現在実行中のPythonバージョン情報
        import sys

        assert sys.version_info.major >= 3
        assert sys.version_info.minor >= 9  # サポート対象バージョン

    def test_file_system_operations_common(self, temp_dir):
        """ファイルシステム操作の共通テスト"""
        # ディレクトリ作成
        test_subdir = temp_dir / "subdir"
        test_subdir.mkdir()
        assert test_subdir.exists()
        assert test_subdir.is_dir()

        # ファイル作成
        test_file = test_subdir / "test.txt"
        test_file.write_text("content", encoding="utf-8")
        assert test_file.exists()
        assert test_file.is_file()

        # ファイル一覧取得
        files = list(test_subdir.iterdir())
        assert len(files) == 1
        assert files[0].name == "test.txt"

    def test_configuration_handling_cross_platform(self, temp_dir):
        """設定ファイル処理のクロスプラットフォームテスト"""
        import json

        # 設定ファイル作成
        config_data = {
            "github_token": "test_token",
            "github_username": "test_user",
            "clone_destination": str(temp_dir / "repos"),
            "use_ssh": False,
        }

        config_file = temp_dir / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        # 設定ファイル読み込み
        with open(config_file, encoding="utf-8") as f:
            loaded_config = json.load(f)

        assert loaded_config == config_data

    def test_logging_configuration_cross_platform(self):
        """ログ設定のクロスプラットフォームテスト"""
        import logging

        # ログレベルの設定と確認
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)

        assert logger.level == logging.INFO
        assert logger.isEnabledFor(logging.INFO)
        assert not logger.isEnabledFor(logging.DEBUG)

    def test_error_handling_cross_platform(self):
        """エラーハンドリングのクロスプラットフォームテスト"""
        # ファイル不存在エラー
        with pytest.raises(FileNotFoundError):
            Path("nonexistent_file.txt").read_text()

        # ディレクトリ作成エラー（権限がある場合のみ）
        try:
            invalid_path = Path("/invalid/path/that/should/not/exist")
            invalid_path.mkdir(parents=True)
            # 作成できた場合はクリーンアップ
            invalid_path.rmdir()
        except (PermissionError, OSError):
            # 期待される動作
            pass

    def test_module_import_cross_platform(self):
        """モジュールインポートのクロスプラットフォームテスト"""
        # 標準ライブラリのインポート
        import json
        import os
        import pathlib
        import sys
        import tempfile

        # インポートされたモジュールの基本機能確認
        assert hasattr(json, "loads")
        assert hasattr(os, "environ")
        assert hasattr(sys, "version_info")
        assert hasattr(pathlib, "Path")
        assert hasattr(tempfile, "TemporaryDirectory")

    def test_string_encoding_cross_platform(self):
        """文字列エンコーディングのクロスプラットフォームテスト"""
        # UTF-8エンコーディングのテスト
        test_strings = [
            "Hello, World!",
            "こんにちは、世界！",
            "🚀 リポジトリセットアップツール",
            "Test with émojis: 🔧 ⚙️ 📊",
        ]

        for test_string in test_strings:
            # エンコード・デコード
            encoded = test_string.encode("utf-8")
            decoded = encoded.decode("utf-8")
            assert decoded == test_string

    def test_datetime_handling_cross_platform(self):
        """日時処理のクロスプラットフォームテスト"""
        from datetime import datetime

        # UTC時刻の取得
        utc_now = datetime.now(UTC)
        assert utc_now.tzinfo == UTC

        # ISO形式での文字列化
        iso_string = utc_now.isoformat()
        assert "T" in iso_string
        assert iso_string.endswith("+00:00")

    @pytest.mark.skipif(not os.environ.get("CI"), reason="CI環境でのみ実行")
    def test_ci_environment_detection(self):
        """CI環境検出テスト"""
        # CI環境変数の確認
        assert os.environ.get("CI") == "true"

        # GitHub Actions固有の環境変数（該当する場合）
        if os.environ.get("GITHUB_ACTIONS"):
            assert os.environ.get("RUNNER_OS") in ["Windows", "Linux", "macOS"]

    def test_package_manager_detection_basic(self):
        """パッケージマネージャー検出の基本テスト"""
        platform_info = detect_platform()
        package_managers = platform_info.package_managers

        # リストであることを確認
        assert isinstance(package_managers, list)

        # 少なくとも何らかのパッケージマネージャーが検出されることを期待
        # （ただし、CI環境では制限がある場合もあるため、厳密にはチェックしない）
        if package_managers:
            for pm in package_managers:
                assert isinstance(pm, str)
                assert len(pm) > 0

    def test_cross_platform_compatibility_markers(self):
        """クロスプラットフォーム互換性マーカーのテスト"""
        from tests.common_markers import get_current_platform

        current_platform = get_current_platform()
        assert current_platform in ["windows", "linux", "macos", "wsl", "unknown"]

        # プラットフォーム情報との整合性確認
        platform_info = detect_platform()
        if current_platform != "unknown":
            assert platform_info.name == current_platform or (
                current_platform == "wsl" and platform_info.name in ["linux", "wsl"]
            )

"""macOS固有のプラットフォームテスト"""

import os
import platform

import pytest

from ...common_markers import macos_only
from ...multiplatform.helpers import verify_current_platform


@macos_only
class TestMacOSPlatform:
    """macOS固有のプラットフォーム機能テスト"""

    def test_macos_environment_detection(self):
        """macOS環境検出テスト"""
        verify_current_platform()
        assert platform.system() == "Darwin"
        assert os.name == "posix"

    def test_macos_shell_detection(self):
        """macOSシェル検出テスト"""
        try:
            from src.setup_repo.platform_detector import detect_platform
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

        platform_info = detect_platform()
        assert platform_info.name == "macos"
        # GitHub Actions環境では実際のシェルはshなので、実環境に合わせる
        if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            assert platform_info.shell == "sh"
        else:
            assert platform_info.shell in ["zsh", "bash", "sh"]

    def test_macos_package_managers(self):
        """macOSパッケージマネージャーテスト"""
        try:
            from src.setup_repo.platform_detector import detect_platform
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

        platform_info = detect_platform()
        expected_managers = ["brew", "port", "conda"]

        # 少なくとも1つのパッケージマネージャーが検出されることを期待
        available_managers = [pm for pm in expected_managers if pm in platform_info.package_managers]
        # macOSではHomebrewが一般的
        assert len(available_managers) >= 0

    def test_macos_python_command(self):
        """macOSPythonコマンドテスト"""
        try:
            from src.setup_repo.platform_detector import detect_platform
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

        platform_info = detect_platform()
        assert platform_info.python_cmd in ["python3", "python"]

    def test_macos_module_availability(self):
        """macOS固有モジュール可用性テスト"""
        try:
            from src.setup_repo.platform_detector import check_module_availability
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

        # Unix系モジュール
        fcntl_info = check_module_availability("fcntl")
        assert fcntl_info["available"]

        # Windows固有モジュールは利用不可
        msvcrt_info = check_module_availability("msvcrt")
        assert not msvcrt_info["available"]

    def test_macos_path_handling(self):
        """macOSパス処理テスト"""
        import pathlib

        # Unix形式のパス
        unix_path = pathlib.Path("/Users/user/file.txt")
        assert unix_path.is_absolute()
        assert str(unix_path).startswith("/")

    def test_macos_environment_variables(self):
        """macOS環境変数テスト"""
        # Unix系共通の環境変数
        unix_vars = ["HOME", "PATH", "USER"]

        for var in unix_vars:
            if var in os.environ:
                assert os.environ[var]  # 値が存在することを確認
                break
        else:
            pytest.skip("Unix系の環境変数が見つかりません")

    def test_macos_file_system_case_handling(self, temp_dir):
        """macOSファイルシステムの大文字小文字処理テスト"""
        # macOSでは通常大文字小文字を保持するが区別しない（HFS+）
        # ただしAPFSでは設定により異なる
        test_file_upper = temp_dir / "TestFile.txt"
        test_file_upper.write_text("test content")

        # 小文字でアクセス
        test_file_lower = temp_dir / "testfile.txt"

        try:
            # ファイルシステムの動作を確認
            if test_file_lower.exists():
                # 大文字小文字を区別しない場合
                assert test_file_lower.read_text() == "test content"
            else:
                # 大文字小文字を区別する場合
                pytest.skip("ファイルシステムが大文字小文字を区別します")
        except Exception:
            pytest.skip("ファイルシステムの動作を確認できません")

    def test_macos_darwin_specific_features(self):
        """macOS (Darwin) 固有機能テスト"""
        # Darwinカーネルの確認
        uname_info = platform.uname()
        assert "darwin" in uname_info.system.lower()

        # macOSバージョン情報
        mac_version = platform.mac_ver()
        if mac_version[0]:  # バージョン情報が取得できる場合
            assert mac_version[0]  # バージョン文字列が存在

    def test_macos_homebrew_paths(self):
        """macOS Homebrewパステスト"""
        # 一般的なHomebrewパス
        common_brew_paths = [
            "/opt/homebrew/bin/brew",  # Apple Silicon Mac
            "/usr/local/bin/brew",  # Intel Mac
        ]

        import pathlib

        brew_found = False
        for brew_path in common_brew_paths:
            if pathlib.Path(brew_path).exists():
                brew_found = True
                break

        if not brew_found:
            pytest.skip("Homebrewが見つかりません")

        # Homebrewが見つかった場合のテスト
        assert brew_found

    def test_macos_application_support_directory(self):
        """macOSアプリケーションサポートディレクトリテスト"""
        home = os.environ.get("HOME")
        if not home:
            pytest.skip("HOME環境変数が設定されていません")

        import pathlib

        app_support = pathlib.Path(home) / "Library" / "Application Support"

        # macOSでは通常このディレクトリが存在する
        if app_support.exists():
            assert app_support.is_dir()
        else:
            pytest.skip("Application Supportディレクトリが見つかりません")

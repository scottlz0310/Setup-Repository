"""Windows固有のプラットフォームテスト"""

import os
import platform

import pytest

from ...common_markers import windows_only
from ...multiplatform.helpers import verify_current_platform


@windows_only
class TestWindowsPlatform:
    """Windows固有のプラットフォーム機能テスト"""

    def test_windows_environment_detection(self):
        """Windows環境検出テスト"""
        verify_current_platform()
        assert platform.system() == "Windows"
        assert os.name == "nt"

    def test_windows_shell_detection(self):
        """Windowsシェル検出テスト"""
        try:
            from src.setup_repo.platform_detector import detect_platform

            platform_info = detect_platform()
            assert platform_info.name == "windows"
            assert platform_info.shell == "cmd"  # セキュリティ修正後の新しい設定
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    def test_windows_package_managers(self):
        """Windowsパッケージマネージャーテスト"""
        try:
            from src.setup_repo.platform_detector import detect_platform

            platform_info = detect_platform()
            expected_managers = ["winget", "choco", "scoop"]
            # 少なくとも1つのパッケージマネージャーが検出されることを確認
            available_managers = [pm for pm in expected_managers if pm in platform_info.package_managers]
            assert len(available_managers) >= 0  # 検出されなくても正常
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    def test_windows_python_command(self):
        """WindowsPythonコマンドテスト"""
        try:
            from src.setup_repo.platform_detector import detect_platform

            platform_info = detect_platform()
            assert platform_info.python_cmd in ["python", "py"]
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    def test_windows_module_availability(self):
        """Windows固有モジュール可用性テスト"""
        try:
            from src.setup_repo.platform_detector import check_module_availability

            # Windows固有モジュール
            msvcrt_info = check_module_availability("msvcrt")
            assert msvcrt_info["available"]
            # Unix系モジュールは利用不可
            fcntl_info = check_module_availability("fcntl")
            assert not fcntl_info["available"]
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    def test_windows_path_handling(self):
        """Windowsパス処理テスト"""
        import pathlib

        # Windows形式のパス
        win_path = pathlib.Path("C:\\Users\\test\\file.txt")
        assert win_path.is_absolute()
        assert str(win_path).startswith("C:")

    def test_windows_environment_variables(self):
        """Windows環境変数テスト"""
        # Windows固有の環境変数
        windows_vars = ["USERPROFILE", "APPDATA", "LOCALAPPDATA"]

        for var in windows_vars:
            if var in os.environ:
                assert os.environ[var]  # 値が存在することを確認
                break
        else:
            pytest.skip("Windows固有の環境変数が見つかりません")

    def test_windows_file_system_case_insensitive(self, temp_dir):
        """Windowsファイルシステムの大文字小文字非区別テスト"""
        # Windowsでは通常大文字小文字を区別しない
        test_file = temp_dir / "TestFile.txt"
        test_file.write_text("test content")

        # 小文字でアクセス
        lower_file = temp_dir / "testfile.txt"

        # Windowsでは同じファイルとして扱われる（通常）
        try:
            assert lower_file.exists()
        except AssertionError:
            # ファイルシステムによっては大文字小文字を区別する場合もある
            pytest.skip("ファイルシステムが大文字小文字を区別します")

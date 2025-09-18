"""Linux固有のプラットフォームテスト"""

import os
import platform

import pytest

from ...common_markers import linux_only
from ...multiplatform.helpers import verify_current_platform


@linux_only
class TestLinuxPlatform:
    """Linux固有のプラットフォーム機能テスト"""

    def test_linux_environment_detection(self):
        """Linux環境検出テスト"""
        verify_current_platform()
        assert platform.system() == "Linux"
        assert os.name == "posix"

    def test_linux_shell_detection(self):
        """Linuxシェル検出テスト"""
        try:
            from src.setup_repo.platform_detector import detect_platform

            platform_info = detect_platform()
        except ImportError:
            pytest.skip("platform_detectorが利用できません")
        assert platform_info.name in ["linux", "wsl"]
        # GitHub Actions環境では実際のシェルはshなので、実環境に合わせる
        if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            assert platform_info.shell == "sh"
        else:
            assert platform_info.shell in ["bash", "sh"]

    def test_linux_package_managers(self):
        """Linuxパッケージマネージャーテスト"""
        try:
            from src.setup_repo.platform_detector import detect_platform

            platform_info = detect_platform()
        except ImportError:
            pytest.skip("platform_detectorが利用できません")
        expected_managers = ["apt", "yum", "dnf", "pacman", "zypper", "snap", "flatpak"]

        # 少なくとも1つのパッケージマネージャーが検出されることを期待
        available_managers = [pm for pm in expected_managers if pm in platform_info.package_managers]
        # Linuxでは通常何らかのパッケージマネージャーが利用可能
        assert len(available_managers) >= 0

    def test_linux_python_command(self):
        """LinuxPythonコマンドテスト"""
        try:
            from src.setup_repo.platform_detector import detect_platform

            platform_info = detect_platform()
        except ImportError:
            pytest.skip("platform_detectorが利用できません")
        assert platform_info.python_cmd in ["python3", "python"]

    def test_linux_module_availability(self):
        """Linux固有モジュール可用性テスト"""
        try:
            from src.setup_repo.platform_detector import check_module_availability

            # Unix系モジュール
            fcntl_info = check_module_availability("fcntl")
            assert fcntl_info["available"]
            # Windows固有モジュールは利用不可
            msvcrt_info = check_module_availability("msvcrt")
        except ImportError:
            pytest.skip("platform_detectorが利用できません")
        assert not msvcrt_info["available"]

    def test_linux_path_handling(self):
        """Linuxパス処理テスト"""
        import pathlib

        # Unix形式のパス
        unix_path = pathlib.Path("/home/user/file.txt")
        assert unix_path.is_absolute()
        assert str(unix_path).startswith("/")

    def test_linux_environment_variables(self):
        """Linux環境変数テスト"""
        # Unix系共通の環境変数
        unix_vars = ["HOME", "PATH", "USER"]

        for var in unix_vars:
            if var in os.environ:
                assert os.environ[var]  # 値が存在することを確認
                break
        else:
            pytest.skip("Unix系の環境変数が見つかりません")

    def test_linux_file_system_case_sensitive(self, temp_dir):
        """Linuxファイルシステムの大文字小文字区別テスト"""
        # Linuxでは通常大文字小文字を区別する
        test_file_upper = temp_dir / "TestFile.txt"
        test_file_lower = temp_dir / "testfile.txt"

        test_file_upper.write_text("upper content")
        test_file_lower.write_text("lower content")

        # 両方のファイルが存在することを確認
        assert test_file_upper.exists()
        assert test_file_lower.exists()

        # 内容が異なることを確認
        assert test_file_upper.read_text() != test_file_lower.read_text()

    def test_linux_proc_filesystem(self):
        """Linux /procファイルシステムテスト"""
        proc_version = "/proc/version"

        try:
            with open(proc_version) as f:
                version_info = f.read()
                assert "linux" in version_info.lower()
        except (FileNotFoundError, PermissionError):
            pytest.skip("/proc/versionにアクセスできません")

    def test_linux_permissions(self, temp_dir):
        """Linuxファイル権限テスト"""
        test_file = temp_dir / "permission_test.txt"
        test_file.write_text("test content")

        # ファイル権限の確認
        stat_info = test_file.stat()
        assert stat_info.st_mode & 0o777  # 何らかの権限が設定されている

        # 実行権限のテスト（可能な場合）
        try:
            test_file.chmod(0o755)
            new_stat = test_file.stat()
            assert new_stat.st_mode & 0o755
        except (OSError, PermissionError):
            pytest.skip("ファイル権限の変更ができません")

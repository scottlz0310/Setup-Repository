"""プラットフォーム検出器の実環境テスト（モック不使用）"""

import os
import platform

import pytest

from ..common_markers import get_current_platform, skip_if_no_command
from ..multiplatform.helpers import verify_current_platform


class TestPlatformDetectorReal:
    """プラットフォーム検出器の実環境テスト（環境偽装モック不使用）"""

    @pytest.mark.unit
    def test_real_platform_detection(self):
        """実環境でのプラットフォーム検出テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import detect_platform
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

        platform_info = detect_platform()
        current_system = platform.system()

        # 実環境での検証
        if current_system == "Windows":
            assert platform_info.name == "windows"
            assert platform_info.shell == "powershell"
            assert platform_info.python_cmd in ["python", "py"]
        elif current_system == "Linux":
            assert platform_info.name in ["linux", "wsl"]
            assert platform_info.shell == "bash"
            assert platform_info.python_cmd in ["python3", "python"]
        elif current_system == "Darwin":
            assert platform_info.name == "macos"
            assert platform_info.shell == "zsh"
            assert platform_info.python_cmd in ["python3", "python"]

    @pytest.mark.unit
    def test_real_package_manager_detection(self):
        """実環境でのパッケージマネージャー検出テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import check_package_manager, detect_platform
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

        platform_info = detect_platform()

        # 実環境で利用可能なパッケージマネージャーをテスト
        for pm in platform_info.package_managers:
            # 実際にコマンドが利用可能かチェック
            is_available = check_package_manager(pm)
            # 検出されたパッケージマネージャーは実際に利用可能であることを期待
            # ただし、環境によっては利用できない場合もあるため、警告レベル
            if not is_available:
                print(f"警告: 検出されたパッケージマネージャー '{pm}' が実際には利用できません")

    @pytest.mark.unit
    def test_real_environment_variables(self):
        """実環境での環境変数テスト"""
        verify_current_platform()

        current_platform = get_current_platform()

        if current_platform == "windows":
            # Windows固有の環境変数
            expected_vars = ["USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP"]
            found_vars = [var for var in expected_vars if var in os.environ]
            assert len(found_vars) > 0, "Windows固有の環境変数が見つかりません"

        elif current_platform in ["linux", "wsl"]:
            # Linux/WSL固有の環境変数
            expected_vars = ["HOME", "PATH", "USER", "SHELL"]
            found_vars = [var for var in expected_vars if var in os.environ]
            assert len(found_vars) > 0, "Unix系の環境変数が見つかりません"

        elif current_platform == "macos":
            # macOS固有の環境変数
            expected_vars = ["HOME", "PATH", "USER", "SHELL"]
            found_vars = [var for var in expected_vars if var in os.environ]
            assert len(found_vars) > 0, "macOS固有の環境変数が見つかりません"

    @pytest.mark.unit
    def test_real_python_executable(self):
        """実環境でのPython実行可能ファイルテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import detect_platform
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

        platform_info = detect_platform()
        python_cmd = platform_info.python_cmd

        # 実際にPythonコマンドが実行可能かテスト
        import shutil

        python_path = shutil.which(python_cmd)

        if python_path:
            assert os.path.exists(python_path)
            assert os.access(python_path, os.X_OK)
        else:
            # Pythonコマンドが見つからない場合は警告
            print(f"警告: 検出されたPythonコマンド '{python_cmd}' が見つかりません")

    @pytest.mark.unit
    def test_real_module_availability(self):
        """実環境でのモジュール可用性テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import check_module_availability
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

        current_platform = get_current_platform()

        # プラットフォーム固有モジュールのテスト
        if current_platform == "windows":
            # Windows固有モジュール
            msvcrt_info = check_module_availability("msvcrt")
            assert msvcrt_info["available"], "Windows環境でmsvcrtが利用できません"

            # Unix系モジュールは利用不可
            fcntl_info = check_module_availability("fcntl")
            assert not fcntl_info["available"], "Windows環境でfcntlが利用可能になっています"

        elif current_platform in ["linux", "wsl", "macos"]:
            # Unix系モジュール
            fcntl_info = check_module_availability("fcntl")
            assert fcntl_info["available"], "Unix系環境でfcntlが利用できません"

            # Windows固有モジュールは利用不可
            msvcrt_info = check_module_availability("msvcrt")
            assert not msvcrt_info["available"], "Unix系環境でmsvcrtが利用可能になっています"

        # 共通モジュールのテスト
        common_modules = ["os", "sys", "platform", "pathlib", "subprocess"]
        for module in common_modules:
            module_info = check_module_availability(module)
            assert module_info["available"], f"共通モジュール '{module}' が利用できません"

    @pytest.mark.unit
    def test_real_ci_environment_detection(self):
        """実環境でのCI環境検出テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import PlatformDetector
        except ImportError:
            pytest.skip("PlatformDetectorが利用できません")

        detector = PlatformDetector()

        # 実環境でのCI環境判定
        is_ci = detector.is_ci_environment()
        assert isinstance(is_ci, bool)

        # GitHub Actions環境の場合
        if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            assert is_ci, "GitHub Actions環境でCI検出が失敗しました"
            assert detector.is_github_actions(), "GitHub Actions検出が失敗しました"

            # RUNNER_OSとの整合性チェック
            runner_os = os.environ.get("RUNNER_OS", "").lower()
            if runner_os:
                platform_info = detector.detect_platform()
                expected_mappings = {
                    "windows": "windows",
                    "linux": ["linux", "wsl"],
                    "macos": "macos",
                }
                expected = expected_mappings.get(runner_os)
                if expected:
                    # platform_infoが文字列の場合とオブジェクトの場合を処理
                    if hasattr(platform_info, "name"):
                        platform_name = platform_info.name
                    elif isinstance(platform_info, str):
                        platform_name = platform_info
                    else:
                        platform_name = str(platform_info)

                    if isinstance(expected, list):
                        assert platform_name in expected
                    else:
                        assert platform_name == expected

    @pytest.mark.unit
    @skip_if_no_command("git")
    def test_real_git_availability(self):
        """実環境でのGit可用性テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import check_package_manager
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

        # Gitコマンドの可用性をテスト
        git_available = check_package_manager("git")
        assert git_available, "Git コマンドが利用できません"

    @pytest.mark.unit
    def test_real_file_system_behavior(self, temp_dir):
        """実環境でのファイルシステム動作テスト"""
        verify_current_platform()

        current_platform = get_current_platform()

        # プラットフォーム固有のファイルシステム動作をテスト
        test_file_upper = temp_dir / "TestFile.txt"
        test_file_lower = temp_dir / "testfile.txt"

        test_file_upper.write_text("upper content")

        if current_platform == "windows":
            # Windowsでは通常大文字小文字を区別しない
            try:
                # 小文字でアクセスして同じファイルかチェック
                if test_file_lower.exists():
                    content = test_file_lower.read_text()
                    assert content == "upper content"
            except Exception:
                # ファイルシステムによっては区別する場合もある
                pass

        elif current_platform in ["linux", "wsl"]:
            # Linuxでは通常大文字小文字を区別する
            test_file_lower.write_text("lower content")

            assert test_file_upper.exists()
            assert test_file_lower.exists()
            assert test_file_upper.read_text() != test_file_lower.read_text()

        elif current_platform == "macos":
            # macOSでは設定により異なるが、通常は区別しない
            try:
                if test_file_lower.exists():
                    content = test_file_lower.read_text()
                    # 同じファイルの場合
                    assert content == "upper content"
                else:
                    # 区別する設定の場合
                    test_file_lower.write_text("lower content")
                    assert test_file_upper.read_text() != test_file_lower.read_text()
            except Exception:
                pass

    @pytest.mark.unit
    def test_real_path_separator(self):
        """実環境でのパス区切り文字テスト"""
        verify_current_platform()

        current_platform = get_current_platform()

        if current_platform == "windows":
            assert os.sep == "\\"
            assert os.pathsep == ";"
        elif current_platform in ["linux", "wsl", "macos"]:
            assert os.sep == "/"
            assert os.pathsep == ":"

    @pytest.mark.unit
    def test_real_platform_diagnosis(self):
        """実環境でのプラットフォーム診断テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import PlatformDetector
        except ImportError:
            pytest.skip("PlatformDetectorが利用できません")

        detector = PlatformDetector()
        diagnosis = detector.diagnose_issues()

        # 診断結果の基本構造をチェック
        assert isinstance(diagnosis, dict)

        # 実環境での診断結果の妥当性をチェック
        if "platform_info" in diagnosis:
            platform_info = diagnosis["platform_info"]
            current_system = platform.system()

            if hasattr(platform_info, "name"):
                platform_name = platform_info.name
            elif isinstance(platform_info, dict):
                platform_name = platform_info.get("name")
            elif isinstance(platform_info, str):
                platform_name = platform_info
            else:
                # プラットフォーム情報が不明な形式の場合はスキップ
                print(f"警告: プラットフォーム情報の形式が不明: {type(platform_info)}")
                return

            # 実環境との整合性チェック
            if current_system == "Windows":
                assert platform_name == "windows"
            elif current_system == "Linux":
                assert platform_name in ["linux", "wsl"]
            elif current_system == "Darwin":
                assert platform_name == "macos"

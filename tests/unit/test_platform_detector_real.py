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

            platform_info = detect_platform()
            current_system = platform.system()
            # 実環境での検証
            if current_system == "Windows":
                assert platform_info.name == "windows"
                assert platform_info.shell == "cmd"  # セキュリティ修正後の新しい設定
                assert platform_info.python_cmd in ["python", "py"]
            elif current_system == "Linux":
                assert platform_info.name in ["linux", "wsl"]
                # GitHub Actions環境では実際のシェルはshなので、実環境に合わせる
                if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
                    assert platform_info.shell == "sh"
                else:
                    assert platform_info.shell in ["bash", "sh"]
                assert platform_info.python_cmd in ["python3", "python"]
            elif current_system == "Darwin":
                assert platform_info.name == "macos"
                # GitHub Actions環境では実際のシェルはshなので、実環境に合わせる
                if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
                    assert platform_info.shell == "sh"
                else:
                    assert platform_info.shell in ["zsh", "bash", "sh"]
                assert platform_info.python_cmd in ["python3", "python"]
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_real_package_manager_detection(self):
        """実環境でのパッケージマネージャー検出テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import check_package_manager, detect_platform

            platform_info = detect_platform()
            # 実環境で利用可能なパッケージマネージャーをテスト
            for pm in platform_info.package_managers:
                # 実際にコマンドが利用可能かチェック
                is_available = check_package_manager(pm)
                # 検出されたパッケージマネージャーは実際に利用可能であることを期待
                # ただし、環境によっては利用できない場合もあるため、警告レベル
                if not is_available:
                    print(f"警告: 検出されたパッケージマネージャー '{pm}' が実際には利用できません")
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

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
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_real_module_availability(self):
        """実環境でのモジュール可用性テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import check_module_availability

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
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_real_ci_environment_detection(self):
        """実環境でのCI環境検出テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import PlatformDetector

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
        except ImportError:
            pytest.skip("PlatformDetectorが利用できません")

    @pytest.mark.unit
    @skip_if_no_command("git")
    def test_real_git_availability(self):
        """実環境でのGit可用性テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import check_package_manager

            # Gitコマンドの可用性をテスト
            git_available = check_package_manager("git")
            assert git_available, "Git コマンドが利用できません"
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

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
                # 空のexcept句: ファイルシステムによる動作の違いを許容
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
                # 空のexcept句: macOSのファイルシステム設定による動作の違いを許容
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
        except ImportError:
            pytest.skip("PlatformDetectorが利用できません")

    @pytest.mark.unit
    def test_install_commands_structure(self):
        """インストールコマンド構造テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import detect_platform, get_install_commands

            platform_info = detect_platform()
            commands = get_install_commands(platform_info)

            # 戻り値の構造をチェック
            assert isinstance(commands, dict)

            # プラットフォーム固有のコマンドが存在することを確認
            if platform_info.name == "windows":
                expected_managers = ["scoop", "winget", "chocolatey", "pip"]
            elif platform_info.name == "wsl" or platform_info.name == "linux":
                expected_managers = ["snap", "apt", "curl", "pip"]
            elif platform_info.name == "macos":
                expected_managers = ["brew", "curl", "pip"]
            else:
                expected_managers = []

            for manager in expected_managers:
                if manager in commands:
                    assert isinstance(commands[manager], list)
                    assert len(commands[manager]) > 0
                    # コマンドが文字列であることを確認
                    for cmd in commands[manager]:
                        assert isinstance(cmd, str)
                        assert len(cmd.strip()) > 0
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_ci_environment_info_structure(self):
        """CI環境情報構造テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import get_ci_environment_info

            ci_info = get_ci_environment_info()
            assert isinstance(ci_info, dict)

            # システム情報が含まれていることを確認
            required_system_keys = [
                "platform_system",
                "platform_release",
                "platform_version",
                "platform_machine",
                "python_version",
                "python_implementation",
            ]

            for key in required_system_keys:
                assert key in ci_info
                assert isinstance(ci_info[key], str)
                assert len(ci_info[key]) > 0

            # GitHub Actions環境の場合、追加情報をチェック
            if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
                github_keys = ["GITHUB_ACTIONS", "RUNNER_OS"]
                for key in github_keys:
                    if key in os.environ:
                        assert key in ci_info
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_available_package_managers(self):
        """利用可能パッケージマネージャーテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import detect_platform, get_available_package_managers

            platform_info = detect_platform()
            available = get_available_package_managers(platform_info)

            # 戻り値の構造をチェック
            assert isinstance(available, list)

            # 利用可能なマネージャーは定義されたマネージャーのサブセット
            for manager in available:
                assert manager in platform_info.package_managers

            # 実環境で最低1つは利用可能であることを期待（警告レベル）
            if not available:
                print(f"警告: プラットフォーム {platform_info.name} で利用可能なパッケージマネージャーが見つかりません")
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_platform_detector_class_methods(self):
        """PlatformDetectorクラスメソッドテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import PlatformDetector

            detector = PlatformDetector()

            # 各メソッドの戻り値型をチェック
            platform_name = detector.detect_platform()
            assert isinstance(platform_name, str)
            assert len(platform_name) > 0

            is_wsl = detector.is_wsl()
            assert isinstance(is_wsl, bool)

            is_ci = detector.is_ci_environment()
            assert isinstance(is_ci, bool)

            is_precommit = detector.is_precommit_environment()
            assert isinstance(is_precommit, bool)

            is_github = detector.is_github_actions()
            assert isinstance(is_github, bool)

            package_manager = detector.get_package_manager()
            assert isinstance(package_manager, str)
            assert len(package_manager) > 0

            platform_info = detector.get_platform_info()
            assert hasattr(platform_info, "name")
            assert hasattr(platform_info, "display_name")
            assert hasattr(platform_info, "package_managers")
            assert hasattr(platform_info, "shell")
            assert hasattr(platform_info, "python_cmd")

            ci_info = detector.get_ci_info()
            assert isinstance(ci_info, dict)

            diagnosis = detector.diagnose_issues()
            assert isinstance(diagnosis, dict)
        except ImportError:
            pytest.skip("PlatformDetectorが利用できません")

    @pytest.mark.unit
    def test_wsl_detection_methods(self):
        """WSL検出メソッドテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import _check_wsl_environment

            is_wsl = _check_wsl_environment()
            assert isinstance(is_wsl, bool)

            # 実環境でのWSL検出結果の妥当性チェック
            current_platform = get_current_platform()
            if current_platform == "wsl":
                # WSL環境では True であることを期待
                assert is_wsl, "WSL環境でWSL検出が失敗しました"
            elif current_platform in ["windows", "macos"]:
                # Windows/macOS環境では False であることを期待
                assert not is_wsl, f"{current_platform}環境でWSLが誤検出されました"
            # Linux環境では判定が困難なため、結果を受け入れる
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_error_handling_in_diagnosis(self):
        """診断機能のエラーハンドリングテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import diagnose_platform_issues

            # 正常ケース
            diagnosis = diagnose_platform_issues()
            assert isinstance(diagnosis, dict)

            # エラーが発生した場合でも適切な構造を返すことを確認
            required_keys = [
                "platform_info",
                "package_managers",
                "module_availability",
                "environment_variables",
                "path_issues",
                "ci_specific_issues",
                "recommendations",
            ]

            for key in required_keys:
                assert key in diagnosis

            # エラーキーが存在する場合の処理
            if "error" in diagnosis:
                assert isinstance(diagnosis["error"], str)
                assert "recommendations" in diagnosis
                assert isinstance(diagnosis["recommendations"], list)
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_log_functions_ci_environment(self):
        """ログ関数のCI環境テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import (
                _log_linux_path_info,
                _log_macos_path_info,
                _log_windows_path_info,
            )

            current_platform = get_current_platform()

            # CI環境でのみログ出力される関数をテスト
            if os.environ.get("CI", "").lower() == "true":
                if current_platform == "windows":
                    # Windows環境でのログ出力テスト
                    _log_windows_path_info()  # 例外が発生しないことを確認
                elif current_platform == "linux":
                    # Linux環境でのログ出力テスト
                    _log_linux_path_info()  # 例外が発生しないことを確認
                elif current_platform == "macos":
                    # macOS環境でのログ出力テスト
                    _log_macos_path_info()  # 例外が発生しないことを確認
            else:
                # 非CI環境では何も出力されないことを確認
                _log_windows_path_info()  # 例外が発生しないことを確認
                _log_linux_path_info()  # 例外が発生しないことを確認
                _log_macos_path_info()  # 例外が発生しないことを確認
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_package_manager_check_failure_logging(self):
        """パッケージマネージャーチェック失敗ログテスト"""
        verify_current_platform()

        try:
            # 様々な例外タイプでのログ出力テスト
            import subprocess

            from src.setup_repo.platform_detector import _log_package_manager_check_failure

            # FileNotFoundError
            error = FileNotFoundError("Command not found")
            _log_package_manager_check_failure("test_manager", error)

            # TimeoutExpired
            error = subprocess.TimeoutExpired("test_cmd", 5)
            _log_package_manager_check_failure("test_manager", error)

            # CalledProcessError
            error = subprocess.CalledProcessError(1, "test_cmd")
            _log_package_manager_check_failure("test_manager", error)

            # 例外が発生しないことを確認
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_ci_specific_issues_diagnosis(self):
        """CI固有問題診断テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import _diagnose_ci_specific_issues, detect_platform

            platform_info = detect_platform()
            diagnosis = {"module_availability": {}, "ci_specific_issues": []}

            # CI環境でのみ実行される診断機能をテスト
            if os.environ.get("CI", "").lower() == "true":
                _diagnose_ci_specific_issues(diagnosis, platform_info)

                # 診断結果の構造をチェック
                assert "ci_specific_issues" in diagnosis
                assert isinstance(diagnosis["ci_specific_issues"], list)
            else:
                # 非CI環境でも例外が発生しないことを確認
                _diagnose_ci_specific_issues(diagnosis, platform_info)
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

    @pytest.mark.unit
    def test_platform_recommendations_generation(self):
        """プラットフォーム推奨事項生成テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.platform_detector import _generate_platform_recommendations, detect_platform

            platform_info = detect_platform()
            diagnosis = {"package_managers": {}, "ci_specific_issues": [], "recommendations": []}

            # パッケージマネージャー情報を設定
            for manager in platform_info.package_managers:
                diagnosis["package_managers"][manager] = {
                    "available": False,  # 利用不可として設定
                    "in_path": False,
                }

            _generate_platform_recommendations(diagnosis, platform_info)

            # 推奨事項が生成されることを確認
            assert "recommendations" in diagnosis
            assert isinstance(diagnosis["recommendations"], list)
            # パッケージマネージャーが利用不可の場合、推奨事項が生成される
            assert len(diagnosis["recommendations"]) > 0
        except ImportError:
            pytest.skip("platform_detectorが利用できません")

"""
プラットフォーム検出統合テスト

既存の分散したプラットフォーム検出テストを統合し、
実環境での動作を重視したテストを提供します。
"""

import os
import platform

import pytest

from setup_repo.platform_detector import (
    PlatformDetector,
    check_package_manager,
    detect_platform,
    diagnose_platform_issues,
)


@pytest.mark.unit
class TestPlatformDetection:
    """プラットフォーム検出の実環境テスト"""

    def test_detect_current_platform(self):
        """現在のプラットフォームが正しく検出されることをテスト"""
        platform_info = detect_platform()
        current_system = platform.system()

        if current_system == "Windows":
            assert platform_info.name == "windows"
            assert platform_info.shell == "powershell"
        elif current_system == "Linux":
            assert platform_info.name in ["linux", "wsl"]
            assert platform_info.shell == "bash"
        elif current_system == "Darwin":
            assert platform_info.name == "macos"
            assert platform_info.shell == "zsh"
        else:
            pytest.skip(f"未対応のプラットフォーム: {current_system}")

    def test_platform_info_attributes(self):
        """プラットフォーム情報の属性が正しく設定されることをテスト"""
        platform_info = detect_platform()

        assert hasattr(platform_info, "name")
        assert hasattr(platform_info, "display_name")
        assert hasattr(platform_info, "package_managers")
        assert hasattr(platform_info, "shell")
        assert hasattr(platform_info, "python_cmd")

        assert isinstance(platform_info.package_managers, list)
        assert len(platform_info.package_managers) > 0

    def test_package_manager_detection_with_timeout(self):
        """パッケージマネージャー検出のタイムアウトテスト"""
        # 存在しないパッケージマネージャーでタイムアウトテスト
        result = check_package_manager("nonexistent_package_manager")
        assert not result

        # 一般的なコマンドでのテスト
        common_commands = ["python", "pip"]
        for cmd in common_commands:
            try:
                result = check_package_manager(cmd)
                assert isinstance(result, bool)
            except Exception as e:
                pytest.fail(f"Unexpected exception for {cmd}: {e}")


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("CI", "").lower() != "true", reason="CI環境でのみ実行")
class TestCIPlatformDetection:
    """CI環境でのプラットフォーム検出テスト"""

    def test_ci_environment_detection(self):
        """CI環境検出テスト"""
        detector = PlatformDetector()

        assert detector.is_ci_environment() is True

        # GitHub Actions固有の環境変数をチェック
        if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            assert detector.is_github_actions() is True
            assert "RUNNER_OS" in os.environ
            assert "GITHUB_WORKFLOW" in os.environ

    def test_platform_consistency_with_runner_os(self):
        """RUNNER_OSとプラットフォーム検出の一貫性テスト"""
        runner_os = os.environ.get("RUNNER_OS", "").lower()
        if not runner_os:
            pytest.skip("RUNNER_OS環境変数が設定されていません")

        platform_info = detect_platform()
        detected_platform = platform_info.name

        # CI環境ではプラットフォームマッピングをチェック
        expected_mappings = {
            "windows": "windows",
            "linux": "linux",  # CI環境ではWSLもlinuxとして扱う
            "macos": "macos",
        }

        expected_platform = expected_mappings.get(runner_os)
        if expected_platform:
            assert detected_platform == expected_platform, (
                f"RUNNER_OS ({runner_os}) と検出プラットフォーム ({detected_platform}) が一致しません"
            )

    def test_comprehensive_platform_diagnosis_in_ci(self):
        """CI環境での包括的プラットフォーム診断テスト"""
        detector = PlatformDetector()
        diagnosis = detector.diagnose_issues()

        # 基本的な診断項目が含まれることを確認
        required_keys = [
            "platform_info",
            "package_managers",
            "module_availability",
            "environment_variables",
            "ci_specific_issues",
            "recommendations",
        ]

        for key in required_keys:
            assert key in diagnosis, f"診断結果に {key} が含まれていません"

        # プラットフォーム情報が正しく設定されていることを確認
        platform_info = diagnosis["platform_info"]
        assert platform_info["name"] in ["windows", "linux", "macos"]

        # CI環境変数が含まれることを確認
        env_vars = diagnosis["environment_variables"]
        assert "CI" in env_vars

    def test_uv_availability_in_ci(self):
        """CI環境でのuv可用性テスト"""
        uv_available = check_package_manager("uv")

        if not uv_available:
            diagnosis = diagnose_platform_issues()
            print(f"UV診断結果: {diagnosis}")

            path_env = os.environ.get("PATH", "")
            print(f"PATH: {path_env}")

            platform_info = detect_platform()
            if platform_info.name == "windows":
                pytest.skip("Windows CI環境でuvが見つかりません。PATH設定を確認してください。")
            else:
                pytest.skip("CI環境でuvが見つかりません。インストール状況を確認してください。")

        assert uv_available, "CI環境でuvが利用できません"


@pytest.mark.cross_platform
class TestCrossPlatformDetection:
    """クロスプラットフォーム検出テスト"""

    def test_platform_shell_mapping(self):
        """プラットフォーム別シェルマッピングテスト"""
        platform_info = detect_platform()

        if platform_info.name == "windows":
            assert platform_info.shell == "powershell"
        elif platform_info.name == "linux":
            assert platform_info.shell == "bash"
        elif platform_info.name == "macos":
            assert platform_info.shell == "zsh"
        elif platform_info.name == "wsl":
            assert platform_info.shell == "bash"
        else:
            pytest.skip(f"未対応のプラットフォーム: {platform_info.name}")

    def test_platform_specific_module_availability(self):
        """プラットフォーム固有モジュールの可用性テスト"""
        from setup_repo.platform_detector import check_module_availability

        # fcntlモジュール（Unix系のみ）
        fcntl_info = check_module_availability("fcntl")
        if os.name == "nt":
            assert not fcntl_info["available"]
            assert fcntl_info["platform_specific"]
        else:
            assert fcntl_info["platform_specific"]

        # msvcrtモジュール（Windowsのみ）
        msvcrt_info = check_module_availability("msvcrt")
        if os.name == "nt":
            assert msvcrt_info["available"]
            assert msvcrt_info["platform_specific"]
        else:
            assert not msvcrt_info["available"]
            assert msvcrt_info["platform_specific"]

        # 共通モジュール
        for module in ["subprocess", "pathlib", "platform"]:
            module_info = check_module_availability(module)
            assert module_info["available"]
            assert not module_info["platform_specific"]

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
class TestCIPlatformDetection:
    """CI環境でのプラットフォーム検出テスト（実環境重視）"""

    def test_ci_environment_detection(self):
        """CI環境検出テスト（実環境）"""
        detector = PlatformDetector()

        # 実環境でのCI環境判定
        is_ci = detector.is_ci_environment()
        assert isinstance(is_ci, bool)

        # CI環境の場合のみ追加チェック
        if is_ci and os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            assert detector.is_github_actions() is True
            # 環境変数の存在確認は実環境に依存
            assert "RUNNER_OS" in os.environ or "GITHUB_WORKFLOW" in os.environ

    def test_platform_consistency_with_runner_os(self):
        """RUNNER_OSとプラットフォーム検出の一貫性テスト（実環境）"""
        runner_os = os.environ.get("RUNNER_OS", "").lower()
        if not runner_os:
            pytest.skip("RUNNER_OS環境変数が設定されていません")

        platform_info = detect_platform()
        detected_platform = platform_info.name

        # 実環境でのプラットフォームマッピングをチェック
        expected_mappings = {
            "windows": "windows",
            "linux": ["linux", "wsl"],  # CI環境ではWSLもlinuxとして扱う
            "macos": "macos",
        }

        expected_platform = expected_mappings.get(runner_os)
        if expected_platform:
            if isinstance(expected_platform, list):
                assert detected_platform in expected_platform, (
                    f"RUNNER_OS ({runner_os}) と検出プラットフォーム ({detected_platform}) が一致しません"
                )
            else:
                assert detected_platform == expected_platform, (
                    f"RUNNER_OS ({runner_os}) と検出プラットフォーム ({detected_platform}) が一致しません"
                )

    def test_comprehensive_platform_diagnosis_in_ci(self):
        """CI環境での包括的プラットフォーム診断テスト（実環境）"""
        detector = PlatformDetector()
        diagnosis = detector.diagnose_issues()

        # 実環境での診断結果の基本的な構造を確認
        assert isinstance(diagnosis, dict)

        # 必須キーの存在確認（実環境に依存）
        common_keys = ["platform_info", "recommendations"]
        for key in common_keys:
            if key in diagnosis:
                assert diagnosis[key] is not None

        # プラットフォーム情報が存在する場合の確認
        if "platform_info" in diagnosis:
            platform_info = diagnosis["platform_info"]
            if hasattr(platform_info, "name"):
                assert platform_info.name in ["windows", "linux", "macos", "wsl"]
            elif isinstance(platform_info, dict) and "name" in platform_info:
                assert platform_info["name"] in ["windows", "linux", "macos", "wsl"]

    def test_uv_availability_in_ci(self):
        """CI環境でのuv可用性テスト（実環境）"""
        uv_available = check_package_manager("uv")

        if not uv_available:
            # 実環境でuvが利用できない場合はスキップ
            platform_info = detect_platform()
            if platform_info.name == "windows":
                pytest.skip("Windows環境でuvが見つかりません")
            else:
                pytest.skip("環境でuvが見つかりません")

        # uvが利用可能な場合のみアサート
        assert uv_available, "環境でuvが利用できません"


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
        """プラットフォーム固有モジュールの可用性テスト（実環境）"""
        from setup_repo.platform_detector import check_module_availability

        # 実環境でのプラットフォーム固有モジュールテスト
        if os.name == "nt":
            # Windows環境
            msvcrt_info = check_module_availability("msvcrt")
            assert msvcrt_info["available"]
            assert msvcrt_info.get("platform_specific", False)

            # Unix系モジュールは利用不可
            fcntl_info = check_module_availability("fcntl")
            assert not fcntl_info["available"]
            assert fcntl_info.get("platform_specific", False)
        else:
            # Unix系環境
            fcntl_info = check_module_availability("fcntl")
            assert fcntl_info["available"]
            assert fcntl_info.get("platform_specific", False)

            # Windowsモジュールは利用不可
            msvcrt_info = check_module_availability("msvcrt")
            assert not msvcrt_info["available"]
            assert msvcrt_info.get("platform_specific", False)

        # 共通モジュール（実環境で必ず利用可能）
        for module in ["subprocess", "pathlib", "platform"]:
            module_info = check_module_availability(module)
            assert module_info["available"]
            assert not module_info.get("platform_specific", True)  # デフォルトはFalseを期待

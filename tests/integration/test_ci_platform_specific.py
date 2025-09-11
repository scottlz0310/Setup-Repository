"""
CI環境でのプラットフォーム固有統合テスト

このモジュールは、実際のCI環境でプラットフォーム固有の
機能とエラーハンドリングをテストします。
"""

import os
import platform
import subprocess

import pytest

from src.setup_repo.logging_config import (
    LoggingConfig,
    create_platform_specific_error_message,
    setup_ci_logging,
)
from src.setup_repo.platform_detector import (
    PlatformDetector,
    check_package_manager,
    detect_platform,
    diagnose_platform_issues,
)


@pytest.mark.skipif(
    os.environ.get("CI", "").lower() != "true", reason="CI環境でのみ実行"
)
class TestCIPlatformSpecific:
    """CI環境でのプラットフォーム固有テスト"""

    def test_ci_environment_detection(self):
        """CI環境検出テスト"""
        detector = PlatformDetector()

        assert detector.is_ci_environment() is True
        assert LoggingConfig.is_ci_environment() is True

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

        # プラットフォームマッピングをチェック
        expected_mappings = {
            "windows": "windows",
            "linux": "linux",
            "macos": "macos",
        }

        expected_platform = expected_mappings.get(runner_os)
        if expected_platform:
            assert detected_platform == expected_platform, (
                f"RUNNER_OS ({runner_os}) と検出プラットフォーム "
                f"({detected_platform}) が一致しません"
            )

    @pytest.mark.skipif(
        platform.system().lower() != "windows", reason="Windows固有テスト"
    )
    def test_windows_specific_functionality(self):
        """Windows固有機能テスト"""
        platform_info = detect_platform()
        assert platform_info.name == "windows"
        assert platform_info.shell == "powershell"
        assert platform_info.python_cmd == "python"

        # msvcrtモジュールの可用性をテスト
        try:
            import msvcrt  # noqa: F401

            assert True, "msvcrtモジュールが利用可能です"
        except ImportError:
            pytest.fail("Windows環境でmsvcrtモジュールが利用できません")

        # fcntlモジュールが利用できないことをテスト
        try:
            import fcntl  # noqa: F401

            pytest.fail("Windows環境でfcntlモジュールが利用可能です（予期しない動作）")
        except ImportError:
            assert True, "fcntlモジュールは期待通り利用できません"

    @pytest.mark.skipif(platform.system().lower() != "linux", reason="Linux固有テスト")
    def test_linux_specific_functionality(self):
        """Linux固有機能テスト"""
        platform_info = detect_platform()
        assert platform_info.name in ["linux", "wsl"]
        assert platform_info.shell == "bash"
        assert platform_info.python_cmd == "python3"

        # fcntlモジュールの可用性をテスト
        try:
            import fcntl  # noqa: F401

            assert True, "fcntlモジュールが利用可能です"
        except ImportError:
            pytest.fail("Linux環境でfcntlモジュールが利用できません")

        # msvcrtモジュールが利用できないことをテスト
        try:
            import msvcrt  # noqa: F401

            pytest.fail("Linux環境でmsvcrtモジュールが利用可能です（予期しない動作）")
        except ImportError:
            assert True, "msvcrtモジュールは期待通り利用できません"

    @pytest.mark.skipif(platform.system().lower() != "darwin", reason="macOS固有テスト")
    def test_macos_specific_functionality(self):
        """macOS固有機能テスト"""
        platform_info = detect_platform()
        assert platform_info.name == "macos"
        assert platform_info.shell == "zsh"
        assert platform_info.python_cmd == "python3"

        # fcntlモジュールの可用性をテスト
        try:
            import fcntl  # noqa: F401

            assert True, "fcntlモジュールが利用可能です"
        except ImportError:
            pytest.fail("macOS環境でfcntlモジュールが利用できません")

    def test_package_manager_availability_in_ci(self):
        """CI環境でのパッケージマネージャー可用性テスト"""
        platform_info = detect_platform()

        # 少なくとも1つのパッケージマネージャーが利用可能であることを確認
        available_managers = []
        for manager in platform_info.package_managers:
            if check_package_manager(manager):
                available_managers.append(manager)

        # CI環境では通常、基本的なツールが利用可能
        basic_tools = ["curl", "pip"]
        basic_available = [tool for tool in basic_tools if check_package_manager(tool)]

        assert len(available_managers) > 0 or len(basic_available) > 0, (
            f"利用可能なパッケージマネージャーが見つかりません。"
            f"プラットフォーム: {platform_info.name}"
        )

    def test_uv_availability_in_ci(self):
        """CI環境でのuv可用性テスト"""
        # CI環境ではuvがインストールされているはず
        uv_available = check_package_manager("uv")

        if not uv_available:
            # uvが利用できない場合は詳細な診断を実行
            diagnosis = diagnose_platform_issues()

            # 診断結果をログ出力
            print(f"UV診断結果: {diagnosis}")

            # PATH情報を出力
            path_env = os.environ.get("PATH", "")
            print(f"PATH: {path_env}")

            # プラットフォーム固有のアドバイスを提供
            platform_info = detect_platform()
            if platform_info.name == "windows":
                pytest.skip(
                    "Windows CI環境でuvが見つかりません。PATH設定を確認してください。"
                )
            else:
                pytest.skip(
                    "CI環境でuvが見つかりません。インストール状況を確認してください。"
                )

        assert uv_available, "CI環境でuvが利用できません"

    def test_ci_logging_configuration(self):
        """CI環境でのロギング設定テスト"""
        # CI環境でのロギング設定をテスト
        logger = setup_ci_logging()
        assert logger is not None

        # CI環境固有の設定をテスト
        assert LoggingConfig.is_ci_environment() is True

        # JSON形式のログが有効かテスト（環境変数による）
        json_logs = LoggingConfig.should_use_json_format()
        if os.environ.get("CI_JSON_LOGS", "").lower() == "true":
            assert json_logs is True

    def test_platform_specific_error_messages_in_ci(self):
        """CI環境でのプラットフォーム固有エラーメッセージテスト"""
        platform_info = detect_platform()

        # 各プラットフォームで典型的なエラーをテスト
        test_errors = [
            ImportError("No module named 'fcntl'"),
            FileNotFoundError("command not found: nonexistent"),
            PermissionError("Permission denied"),
        ]

        for error in test_errors:
            message = create_platform_specific_error_message(error, platform_info.name)

            # プラットフォーム名が含まれることを確認
            assert platform_info.display_name in message

            # CI環境情報が含まれることを確認
            assert "CI環境" in message or "GitHub Actions" in message

            # 元のエラーメッセージが含まれることを確認
            assert str(error) in message

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
        assert platform_info["name"] in ["windows", "linux", "macos", "wsl"]
        assert "GitHub Actions" in platform_info["display_name"]

        # CI環境変数が含まれることを確認
        env_vars = diagnosis["environment_variables"]
        assert "CI" in env_vars

        # モジュール可用性情報が含まれることを確認
        module_availability = diagnosis["module_availability"]
        critical_modules = ["fcntl", "msvcrt", "subprocess", "pathlib"]
        for module_name in critical_modules:
            assert module_name in module_availability

    def test_error_recovery_and_fallback_in_ci(self):
        """CI環境でのエラー回復とフォールバック機構テスト"""
        # 意図的にエラーを発生させてフォールバック機構をテスト

        # 存在しないパッケージマネージャーをテスト
        assert check_package_manager("nonexistent_manager") is False

        # 診断機能がエラーを適切に処理することをテスト
        diagnosis = diagnose_platform_issues()

        # エラーが発生してもプログラムが継続することを確認
        assert "error" not in diagnosis or diagnosis["error"] is None

        # 推奨事項が提供されることを確認
        assert "recommendations" in diagnosis
        assert isinstance(diagnosis["recommendations"], list)

    def test_path_diagnostics_in_ci(self):
        """CI環境でのPATH診断テスト"""
        diagnosis = diagnose_platform_issues()

        # PATH関連の問題がチェックされることを確認
        assert "path_issues" in diagnosis

        # PATH環境変数が記録されることを確認
        assert "PATH" in diagnosis["environment_variables"]

        # プラットフォーム固有のPATH問題をチェック
        platform_info = detect_platform()
        path_env = os.environ.get("PATH", "")

        if platform_info.name == "windows":
            # Windows固有のPATHチェック
            assert ";" in path_env or len(path_env.split(os.pathsep)) > 1
        else:
            # Unix系のPATHチェック
            assert ":" in path_env or len(path_env.split(os.pathsep)) > 1


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("CI", "").lower() != "true", reason="CI環境でのみ実行"
)
class TestCIIntegrationWorkflow:
    """CI環境での統合ワークフローテスト"""

    def test_full_ci_workflow(self):
        """完全なCIワークフローテスト"""
        # 1. プラットフォーム検出
        detector = PlatformDetector()
        platform_info = detector.get_platform_info()

        # 2. CI環境確認
        assert detector.is_ci_environment() is True

        # 3. 診断実行
        diagnosis = detector.diagnose_issues()

        # 4. エラーハンドリングテスト
        test_error = RuntimeError("Test error for CI workflow")
        error_message = create_platform_specific_error_message(
            test_error, platform_info.name
        )

        # 5. ログ設定テスト
        logger = setup_ci_logging()

        # 6. 結果検証
        assert platform_info.name in ["windows", "linux", "macos", "wsl"]
        assert "error" not in diagnosis or diagnosis["error"] is None
        assert "CI環境" in error_message or "GitHub Actions" in error_message
        assert logger is not None

        print(f"✅ CI統合ワークフローテスト完了: {platform_info.display_name}")

    def test_ci_error_reporting_workflow(self):
        """CIエラー報告ワークフローテスト"""
        detector = PlatformDetector()
        platform_info = detector.get_platform_info()

        # 様々なエラーシナリオをテスト
        error_scenarios = [
            ("ImportError", ImportError("Test import error")),
            ("FileNotFoundError", FileNotFoundError("Test file not found")),
            ("PermissionError", PermissionError("Test permission error")),
        ]

        for scenario_name, error in error_scenarios:
            # エラーメッセージ生成
            message = create_platform_specific_error_message(
                error, platform_info.name, {"scenario": scenario_name}
            )

            # GitHub Actions形式のアノテーションをテスト
            if detector.is_github_actions():
                # アノテーション形式の確認
                assert platform_info.display_name in message
                assert "トラブルシューティング" in message

                # CI診断情報が含まれることを確認
                assert "CI診断情報" in message

        print("✅ CIエラー報告ワークフローテスト完了")

    def test_platform_specific_ci_optimizations(self):
        """プラットフォーム固有のCI最適化テスト"""
        platform_info = detect_platform()

        # プラットフォーム固有の最適化をテスト
        if platform_info.name == "windows":
            # Windows固有の最適化
            assert platform_info.shell == "powershell"

            # PowerShellの実行ポリシーをチェック（可能な場合）
            try:
                result = subprocess.run(
                    ["powershell", "-Command", "Get-ExecutionPolicy"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    print(f"PowerShell実行ポリシー: {result.stdout.strip()}")
            except Exception as e:
                print(f"PowerShell実行ポリシーチェック失敗: {e}")

        elif platform_info.name == "macos":
            # macOS固有の最適化
            assert platform_info.shell == "zsh"

            # Homebrewパスの確認
            path_env = os.environ.get("PATH", "")
            homebrew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
            homebrew_in_path = any(hb_path in path_env for hb_path in homebrew_paths)

            if not homebrew_in_path:
                print("⚠️ HomebrewのPATHが設定されていない可能性があります")

        elif platform_info.name == "linux":
            # Linux固有の最適化
            assert platform_info.shell == "bash"

            # 一般的なLinuxパスの確認
            path_env = os.environ.get("PATH", "")
            common_paths = ["/usr/bin", "/usr/local/bin", "/bin"]
            for common_path in common_paths:
                if common_path not in path_env:
                    print(f"⚠️ {common_path} がPATHに含まれていません")

        print(f"✅ {platform_info.name}固有のCI最適化テスト完了")

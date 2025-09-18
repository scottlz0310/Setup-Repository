"""
Windows固有機能テスト

Windows環境でのみ実行される機能のテスト。
他のプラットフォームでは適切にスキップされます。
"""

import os
import platform
import subprocess

import pytest

from setup_repo.platform_detector import detect_platform


@pytest.mark.windows
class TestWindowsSpecific:
    """Windows固有機能テスト"""

    def setUp(self):
        """テスト前の環境確認"""
        if platform.system() != "Windows":
            pytest.skip("Windows環境でのみ実行")

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows固有機能のテストです",
    )
    def test_windows_platform_detection(self):
        """Windows固有のプラットフォーム検出テスト"""
        platform_info = detect_platform()
        assert platform_info.name == "windows"
        assert platform_info.shell == "cmd"  # セキュリティ修正後の新しい設定
        assert platform_info.python_cmd == "python"

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows固有機能のテストです",
    )
    def test_windows_specific_modules(self):
        """Windows固有モジュールのテスト"""
        # msvcrtモジュールが利用可能であることをテスト
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

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows固有機能のテストです",
    )
    def test_windows_path_handling(self):
        """Windows固有のパス処理テスト"""
        import tempfile
        from pathlib import Path

        # Windowsパスの処理をテスト
        with tempfile.TemporaryDirectory() as temp_dir:
            windows_path = Path(temp_dir) / "test_repo"

            # Windowsスタイルのパス区切り文字をテスト
            path_str = str(windows_path)
            assert "\\" in path_str or "/" in path_str  # どちらでも有効

            # パスの存在確認
            windows_path.mkdir(exist_ok=True)
            assert windows_path.exists()

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows固有機能のテストです",
    )
    def test_windows_environment_variables(self):
        """Windows固有の環境変数テスト"""
        # Windows固有の環境変数をテスト
        windows_env_vars = ["USERPROFILE", "APPDATA", "LOCALAPPDATA"]

        for env_var in windows_env_vars:
            value = os.environ.get(env_var)
            if value:  # CI環境では一部の環境変数が設定されていない場合がある
                assert isinstance(value, str)
                assert len(value) > 0

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows固有機能のテストです",
    )
    def test_windows_powershell_availability(self):
        """PowerShellの可用性テスト"""
        try:
            # PowerShellの実行テスト
            result = subprocess.run(
                ["powershell", "-Command", "Get-Host"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # PowerShellが正常に実行されることを確認
            assert result.returncode == 0 or result.returncode is None

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            # CI環境やサンドボックス環境では制限がある場合
            pytest.skip(f"PowerShell実行テストをスキップ: {e}")

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows固有機能のテストです",
    )
    def test_windows_package_managers(self):
        """Windows固有パッケージマネージャーテスト"""
        from setup_repo.platform_detector import check_package_manager

        # 少なくとも基本的なツールが利用可能であることを確認
        basic_tools = ["python", "pip"]
        available_basic = [tool for tool in basic_tools if check_package_manager(tool)]

        assert len(available_basic) > 0, "基本的なツールが利用できません"

    @pytest.mark.skipif(
        platform.system() != "Windows" or not os.environ.get("CI"),
        reason="Windows CI環境でのみ実行",
    )
    def test_windows_ci_specific_functionality(self):
        """Windows CI環境固有の機能テスト"""
        # GitHub Actions Windows環境での特定の動作をテスト
        if os.environ.get("GITHUB_ACTIONS") == "true":
            runner_os = os.environ.get("RUNNER_OS", "").lower()
            assert runner_os == "windows"

            # Windows CI環境での診断実行
            from setup_repo.platform_detector import diagnose_platform_issues

            diagnosis = diagnose_platform_issues()
            assert diagnosis["platform_info"]["name"] == "windows"

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Windows固有機能のテストです",
    )
    def test_windows_error_handling(self):
        """Windows固有のエラーハンドリングテスト"""
        from setup_repo.logging_config import create_platform_specific_error_message

        # Windows固有のエラーをテスト
        test_error = FileNotFoundError("指定されたファイルが見つかりません")

        error_message = create_platform_specific_error_message(test_error, "windows")

        # Windows固有の情報が含まれることを確認
        assert "Windows" in error_message
        assert str(test_error) in error_message

"""
Unix系固有機能テスト

Linux、WSL、macOS環境でのみ実行される機能のテスト。
Windows環境では適切にスキップされます。
"""

import os
import platform

import pytest

from setup_repo.platform_detector import detect_platform


@pytest.mark.unix
class TestUnixSpecific:
    """Unix系固有機能テスト"""

    def setUp(self):
        """テスト前の環境確認"""
        if platform.system() == "Windows":
            pytest.skip("Unix系環境でのみ実行")

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix系環境でのみ実行",
    )
    def test_unix_platform_detection(self):
        """Unix系固有のプラットフォーム検出テスト"""
        platform_info = detect_platform()
        assert platform_info.name in ["linux", "macos", "wsl"]
        # 実環境ではシェルが sh の場合がある
        assert platform_info.shell in ["sh", "bash", "zsh"]
        assert platform_info.python_cmd == "python3"

    @pytest.mark.skipif(
        os.name == "nt",
        reason="fcntlモジュールはWindows環境では利用できません",
    )
    def test_unix_specific_modules(self):
        """Unix系固有モジュールのテスト"""
        try:
            import fcntl  # noqa: F401

            assert True, "fcntlモジュールが利用可能です"
        except ImportError:
            pytest.skip("fcntlモジュールが利用できません")

        # msvcrtモジュールが利用できないことをテスト
        try:
            import msvcrt  # noqa: F401

            pytest.fail("Unix系環境でmsvcrtモジュールが利用可能です（予期しない動作）")
        except ImportError:
            assert True, "msvcrtモジュールは期待通り利用できません"

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix系環境でのみ実行",
    )
    def test_unix_path_handling(self):
        """Unix系固有のパス処理テスト"""
        import tempfile
        from pathlib import Path

        # Unix系パスの処理をテスト
        with tempfile.TemporaryDirectory() as temp_dir:
            unix_path = Path(temp_dir) / "test_repo"

            # Unix系スタイルのパス区切り文字をテスト
            path_str = str(unix_path)
            assert "/" in path_str

            # パスの存在確認
            unix_path.mkdir(exist_ok=True)
            assert unix_path.exists()

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix系環境でのみ実行",
    )
    def test_unix_environment_variables(self):
        """Unix系固有の環境変数テスト"""
        # Unix系固有の環境変数をテスト
        unix_env_vars = ["HOME", "USER", "PATH"]

        for env_var in unix_env_vars:
            value = os.environ.get(env_var)
            if env_var == "PATH":
                # PATHは必須
                assert value is not None
                assert len(value) > 0
                assert ":" in value or len(value.split(os.pathsep)) > 1
            elif value:  # その他は存在する場合のみチェック
                assert isinstance(value, str)
                assert len(value) > 0

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix系環境でのみ実行",
    )
    def test_unix_shell_availability(self):
        """Unix系シェルの可用性テスト"""
        import subprocess

        platform_info = detect_platform()
        shell = platform_info.shell

        try:
            # シェルの実行テスト
            result = subprocess.run(
                [shell, "-c", "echo 'test'"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # シェルが正常に実行されることを確認
            assert result.returncode == 0
            assert "test" in result.stdout

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            pytest.skip(f"シェル実行テストをスキップ: {e}")

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix系環境でのみ実行",
    )
    def test_unix_package_managers(self):
        """Unix系固有パッケージマネージャーテスト"""
        from setup_repo.platform_detector import check_package_manager

        # 少なくとも基本的なツールが利用可能であることを確認
        basic_tools = ["python3", "pip", "curl"]
        available_basic = [tool for tool in basic_tools if check_package_manager(tool)]

        assert len(available_basic) > 0, "基本的なツールが利用できません"

    @pytest.mark.skipif(
        platform.system() == "Windows" or not os.environ.get("CI"),
        reason="Unix系CI環境でのみ実行",
    )
    def test_unix_ci_specific_functionality(self):
        """Unix系CI環境固有の機能テスト"""
        # GitHub Actions Unix系環境での特定の動作をテスト
        if os.environ.get("GITHUB_ACTIONS") == "true":
            runner_os = os.environ.get("RUNNER_OS", "").lower()
            assert runner_os in ["linux", "macos"]

            # Unix系CI環境での診断実行
            from setup_repo.platform_detector import diagnose_platform_issues

            diagnosis = diagnose_platform_issues()
            assert diagnosis["platform_info"]["name"] in ["linux", "macos", "wsl"]

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix系環境でのみ実行",
    )
    def test_unix_permissions(self):
        """Unix系固有の権限処理テスト"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_permissions.txt"
            test_file.write_text("test content")

            # ファイル権限の確認（基本的なチェックのみ）
            stat_info = test_file.stat()
            assert stat_info.st_mode is not None

            # 実行可能権限のテスト（可能な場合のみ）
            try:
                test_file.chmod(0o755)
                new_stat = test_file.stat()
                assert new_stat.st_mode != stat_info.st_mode
            except (OSError, PermissionError):
                # 権限変更ができない環境ではスキップ
                pytest.skip("権限変更テストをスキップ")

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix系環境でのみ実行",
    )
    def test_unix_error_handling(self):
        """Unix系固有のエラーハンドリングテスト"""
        from setup_repo.logging_config import create_platform_specific_error_message

        platform_info = detect_platform()

        # Unix系固有のエラーをテスト
        test_error = PermissionError("Permission denied")

        error_message = create_platform_specific_error_message(test_error, platform_info.name)

        # Unix系固有の情報が含まれることを確認
        assert platform_info.display_name in error_message
        assert str(test_error) in error_message

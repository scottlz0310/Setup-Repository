"""
macOS固有機能テスト

macOS環境でのみ実行される機能のテスト。
他のプラットフォームでは適切にスキップされます。
"""

import os
import platform
import subprocess

import pytest

from setup_repo.platform_detector import detect_platform


@pytest.mark.macos
class TestMacOSSpecific:
    """macOS固有機能テスト"""

    def setUp(self):
        """テスト前の環境確認"""
        if platform.system() != "Darwin":
            pytest.skip("macOS環境でのみ実行")

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS固有テスト",
    )
    def test_macos_platform_detection(self):
        """macOS固有のプラットフォーム検出テスト"""
        platform_info = detect_platform()
        assert platform_info.name == "macos"
        assert platform_info.shell == "zsh"
        assert platform_info.python_cmd == "python3"

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS固有テスト",
    )
    def test_macos_specific_modules(self):
        """macOS固有モジュールのテスト"""
        # fcntlモジュールが利用可能であることをテスト
        try:
            import fcntl  # noqa: F401

            assert True, "fcntlモジュールが利用可能です"
        except ImportError:
            pytest.fail("macOS環境でfcntlモジュールが利用できません")

        # msvcrtモジュールが利用できないことをテスト
        try:
            import msvcrt  # noqa: F401

            pytest.fail("macOS環境でmsvcrtモジュールが利用可能です（予期しない動作）")
        except ImportError:
            assert True, "msvcrtモジュールは期待通り利用できません"

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS固有テスト",
    )
    def test_macos_path_handling(self):
        """macOS固有のパス処理テスト"""
        import tempfile
        from pathlib import Path

        # macOSパスの処理をテスト
        with tempfile.TemporaryDirectory() as temp_dir:
            macos_path = Path(temp_dir) / "test_repo"

            # Unix系スタイルのパス区切り文字をテスト
            path_str = str(macos_path)
            assert "/" in path_str

            # パスの存在確認
            macos_path.mkdir(exist_ok=True)
            assert macos_path.exists()

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS固有テスト",
    )
    def test_macos_environment_variables(self):
        """macOS固有の環境変数テスト"""
        # macOS固有の環境変数をテスト
        macos_env_vars = ["HOME", "USER", "PATH"]

        for env_var in macos_env_vars:
            value = os.environ.get(env_var)
            if env_var == "PATH":
                # PATHは必須
                assert value is not None
                assert len(value) > 0
                assert ":" in value
            elif value:  # その他は存在する場合のみチェック
                assert isinstance(value, str)
                assert len(value) > 0

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS固有テスト",
    )
    def test_macos_zsh_availability(self):
        """zshの可用性テスト"""
        try:
            # zshの実行テスト
            result = subprocess.run(
                ["zsh", "-c", "echo 'test'"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # zshが正常に実行されることを確認
            assert result.returncode == 0
            assert "test" in result.stdout

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            pytest.skip(f"zsh実行テストをスキップ: {e}")

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS固有テスト",
    )
    def test_macos_homebrew_paths(self):
        """Homebrewパスの確認テスト"""
        path_env = os.environ.get("PATH", "")

        # 一般的なHomebrewパスをチェック
        homebrew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
        homebrew_in_path = any(hb_path in path_env for hb_path in homebrew_paths)

        if not homebrew_in_path:
            # Homebrewが見つからない場合は警告のみ
            pytest.skip("HomebrewのPATHが設定されていない可能性があります")

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS固有テスト",
    )
    def test_macos_package_managers(self):
        """macOS固有パッケージマネージャーテスト"""
        from setup_repo.platform_detector import check_package_manager

        # 少なくとも基本的なツールが利用可能であることを確認
        basic_tools = ["python3", "pip", "curl"]
        available_basic = [tool for tool in basic_tools if check_package_manager(tool)]

        assert len(available_basic) > 0, "基本的なツールが利用できません"

    @pytest.mark.skipif(
        platform.system() != "Darwin" or not os.environ.get("CI"),
        reason="macOS CI環境でのみ実行",
    )
    def test_macos_ci_specific_functionality(self):
        """macOS CI環境固有の機能テスト"""
        # GitHub Actions macOS環境での特定の動作をテスト
        if os.environ.get("GITHUB_ACTIONS") == "true":
            runner_os = os.environ.get("RUNNER_OS", "").lower()
            assert runner_os == "macos"

            # macOS CI環境での診断実行
            from setup_repo.platform_detector import diagnose_platform_issues

            diagnosis = diagnose_platform_issues()
            assert diagnosis["platform_info"]["name"] == "macos"

    @pytest.mark.skipif(
        platform.system() != "Darwin",
        reason="macOS固有テスト",
    )
    def test_macos_permissions(self):
        """macOS固有の権限処理テスト"""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_permissions.txt"
            test_file.write_text("test content")

            # ファイル権限の確認
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
        platform.system() != "Darwin",
        reason="macOS固有テスト",
    )
    def test_macos_error_handling(self):
        """macOS固有のエラーハンドリングテスト"""
        from setup_repo.logging_config import create_platform_specific_error_message

        # macOS固有のエラーをテスト
        test_error = OSError("Operation not permitted")

        error_message = create_platform_specific_error_message(test_error, "macos")

        # macOS固有の情報が含まれることを確認
        assert "macOS" in error_message
        assert str(test_error) in error_message

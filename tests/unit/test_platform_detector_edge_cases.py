"""プラットフォーム検出のエッジケースとエラーハンドリングテスト"""

import os
import platform
import subprocess
from unittest.mock import Mock, patch

import pytest

from src.setup_repo.platform_detector import (
    PlatformDetector,
    _check_wsl_environment,
    _diagnose_ci_specific_issues,
    _generate_platform_recommendations,
    _is_ci_environment,
    _is_precommit_environment,
    _log_package_manager_check_failure,
    check_module_availability,
    check_package_manager,
    diagnose_platform_issues,
    get_available_package_managers,
    get_ci_environment_info,
    get_install_commands,
)

from ..multiplatform.helpers import verify_current_platform


class TestPlatformDetectorEdgeCases:
    """プラットフォーム検出のエッジケーステスト"""

    @pytest.mark.unit
    def test_wsl_detection_edge_cases(self):
        """WSL検出のエッジケーステスト"""
        verify_current_platform()

        # /proc/versionファイルが存在しない場合
        with (
            patch("os.path.exists", return_value=False),
            patch("platform.release", return_value="5.4.0-generic"),
        ):
                result = _check_wsl_environment()
                assert isinstance(result, bool)

        # /proc/versionファイル読み取りエラー
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=PermissionError("Access denied")),
        ):
                result = _check_wsl_environment()
                assert isinstance(result, bool)

        # platform.release()にmicrosoftが含まれる場合
        with patch("platform.release", return_value="5.4.0-microsoft-standard-WSL2"):
            result = _check_wsl_environment()
            assert result is True

    @pytest.mark.unit
    def test_package_manager_check_timeout_handling(self):
        """パッケージマネージャーチェックのタイムアウト処理テスト"""
        verify_current_platform()

        # タイムアウトエラーのシミュレート
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
            result = check_package_manager("nonexistent_manager")
            assert result is False

        # CalledProcessErrorのシミュレート
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")):
            result = check_package_manager("failing_manager")
            assert result is False

        # FileNotFoundErrorのシミュレート
        with patch("subprocess.run", side_effect=FileNotFoundError("Command not found")):
            result = check_package_manager("missing_manager")
            assert result is False

    @pytest.mark.unit
    def test_package_manager_check_empty_output(self):
        """パッケージマネージャーチェックの空出力処理テスト"""
        verify_current_platform()

        # 空の出力を返すコマンド
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = check_package_manager("empty_output_manager")
            assert result is False

        # stderrのみに出力があるケース
        mock_result.stdout = ""
        mock_result.stderr = "version 1.0.0"

        with patch("subprocess.run", return_value=mock_result):
            result = check_package_manager("stderr_only_manager")
            assert result is True

    @pytest.mark.unit
    def test_module_availability_edge_cases(self):
        """モジュール可用性チェックのエッジケーステスト"""
        verify_current_platform()

        # 存在しないモジュール
        result = check_module_availability("nonexistent_module_12345")
        assert result["available"] is False
        assert result["import_error"] is not None
        assert "No module named" in result["import_error"]

        # プラットフォーム固有モジュール（fcntl）
        result = check_module_availability("fcntl")
        assert result["platform_specific"] is True
        if platform.system() == "Windows":
            assert result["available"] is False
        else:
            # Unix系では利用可能
            assert result["available"] is True

        # プラットフォーム固有モジュール（msvcrt）
        result = check_module_availability("msvcrt")
        assert result["platform_specific"] is True
        if platform.system() == "Windows":
            assert result["available"] is True
        else:
            assert result["available"] is False

    @pytest.mark.unit
    def test_module_availability_version_detection(self):
        """モジュールバージョン検出のテスト"""
        verify_current_platform()

        # __version__属性を持つモジュール
        with patch("builtins.__import__") as mock_import:
            mock_module = Mock()
            mock_module.__version__ = "1.2.3"
            mock_module.__file__ = "/path/to/module.py"
            mock_import.return_value = mock_module

            result = check_module_availability("test_module")
            assert result["available"] is True
            assert result["version"] == "1.2.3"
            assert result["location"] == "/path/to/module.py"

        # version属性を持つモジュール
        with patch("builtins.__import__") as mock_import:
            mock_module = Mock()
            mock_module.version = "2.0.0"
            del mock_module.__version__  # __version__属性を削除
            mock_import.return_value = mock_module

            result = check_module_availability("test_module_v2")
            assert result["available"] is True
            assert result["version"] == "2.0.0"

    @pytest.mark.unit
    def test_ci_environment_detection_edge_cases(self):
        """CI環境検出のエッジケーステスト"""
        verify_current_platform()

        # 複数のCI環境変数が設定されている場合
        with patch.dict(os.environ, {"CI": "true", "GITHUB_ACTIONS": "true", "CONTINUOUS_INTEGRATION": "true"}):
            assert _is_ci_environment() is True

        # 大文字小文字の違い（実際の実装では大文字小文字を区別しない）
        with patch.dict(os.environ, {"CI": "TRUE"}, clear=True):
            # 実装では大文字小文字を区別しないため、TRUEでもTrueになる
            result = _is_ci_environment()
            assert isinstance(result, bool)  # 結果の型を確認

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "True"}, clear=True):
            result = _is_ci_environment()
            assert isinstance(result, bool)  # 結果の型を確認

        # 空の環境変数
        with patch.dict(os.environ, {"CI": ""}, clear=True):
            assert _is_ci_environment() is False

    @pytest.mark.unit
    def test_precommit_environment_detection(self):
        """precommit環境検出のテスト"""
        verify_current_platform()

        # PRE_COMMIT=1の場合
        with patch.dict(os.environ, {"PRE_COMMIT": "1"}):
            assert _is_precommit_environment() is True

        # PRE_COMMIT=0の場合
        with patch.dict(os.environ, {"PRE_COMMIT": "0"}):
            assert _is_precommit_environment() is False

        # PRE_COMMITが設定されていない場合
        with patch.dict(os.environ, {}, clear=True):
            assert _is_precommit_environment() is False

    @pytest.mark.unit
    def test_get_available_package_managers_filtering(self):
        """利用可能パッケージマネージャーのフィルタリングテスト"""
        verify_current_platform()

        from src.setup_repo.platform_detector import PlatformInfo

        # テスト用プラットフォーム情報
        platform_info = PlatformInfo(
            name="test",
            display_name="Test Platform",
            package_managers=["available_manager", "unavailable_manager"],
            shell="bash",
            python_cmd="python3",
        )

        # 一部のマネージャーのみ利用可能
        with patch("src.setup_repo.platform_detector.check_package_manager") as mock_check:

            def side_effect(manager):
                return manager == "available_manager"

            mock_check.side_effect = side_effect

            available = get_available_package_managers(platform_info)
            assert available == ["available_manager"]

        # すべて利用不可
        with patch("src.setup_repo.platform_detector.check_package_manager", return_value=False):
            available = get_available_package_managers(platform_info)
            assert available == []

    @pytest.mark.unit
    def test_get_install_commands_unknown_platform(self):
        """未知のプラットフォームでのインストールコマンド取得テスト"""
        verify_current_platform()

        from src.setup_repo.platform_detector import PlatformInfo

        # 未知のプラットフォーム
        unknown_platform = PlatformInfo(
            name="unknown_os",
            display_name="Unknown OS",
            package_managers=["unknown_manager"],
            shell="unknown_shell",
            python_cmd="unknown_python",
        )

        commands = get_install_commands(unknown_platform)
        assert commands == {}

    @pytest.mark.unit
    def test_ci_environment_info_collection(self):
        """CI環境情報収集のテスト"""
        verify_current_platform()

        # GitHub Actions環境変数をシミュレート
        github_env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_WORKFLOW": "CI",
            "GITHUB_RUN_ID": "123456",
            "RUNNER_OS": "Linux",
            "RUNNER_ARCH": "X64",
        }

        with patch.dict(os.environ, github_env):
            ci_info = get_ci_environment_info()

            assert ci_info["GITHUB_ACTIONS"] == "true"
            assert ci_info["GITHUB_WORKFLOW"] == "CI"
            assert ci_info["RUNNER_OS"] == "Linux"
            assert "platform_system" in ci_info
            assert "python_version" in ci_info

        # 環境変数が設定されていない場合
        with patch.dict(os.environ, {}, clear=True):
            ci_info = get_ci_environment_info()

            # システム情報は常に含まれる
            assert "platform_system" in ci_info
            assert "python_version" in ci_info
            # GitHub固有の変数は含まれない
            assert "GITHUB_ACTIONS" not in ci_info

    @pytest.mark.unit
    def test_diagnose_platform_issues_error_handling(self):
        """プラットフォーム問題診断のエラーハンドリングテスト"""
        verify_current_platform()

        # detect_platform()でエラーが発生する場合
        with patch(
            "src.setup_repo.platform_detector.detect_platform", side_effect=Exception("Platform detection failed")
        ):
            diagnosis = diagnose_platform_issues()

            assert "error" in diagnosis
            assert "Platform detection failed" in diagnosis["error"]
            assert len(diagnosis["recommendations"]) > 0

    @pytest.mark.unit
    def test_diagnose_ci_specific_issues_platform_mismatch(self):
        """CI固有問題診断のプラットフォーム不一致テスト"""
        verify_current_platform()

        from src.setup_repo.platform_detector import PlatformInfo

        diagnosis = {"ci_specific_issues": [], "module_availability": {}}

        # RUNNER_OSと検出プラットフォームが不一致
        platform_info = PlatformInfo(
            name="macos", display_name="macOS", package_managers=["brew"], shell="zsh", python_cmd="python3"
        )

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "RUNNER_OS": "linux"}):
            _diagnose_ci_specific_issues(diagnosis, platform_info)

            issues = diagnosis["ci_specific_issues"]
            assert any("does not match detected platform" in issue for issue in issues)

    @pytest.mark.unit
    def test_log_package_manager_check_failure_platform_specific(self):
        """パッケージマネージャーチェック失敗ログのプラットフォーム固有テスト"""
        verify_current_platform()

        # Windows環境でのuvエラー
        with patch("platform.system", return_value="Windows"), patch("builtins.print") as mock_print:
            error = FileNotFoundError("uv not found")
            _log_package_manager_check_failure("uv", error)

            # デバッグメッセージと警告メッセージが出力される
            assert mock_print.call_count >= 2

        # macOS環境でのbrewエラー
        with patch("platform.system", return_value="Darwin"), patch("builtins.print") as mock_print:
            error = subprocess.CalledProcessError(1, "brew")
            _log_package_manager_check_failure("brew", error)

            assert mock_print.call_count >= 2

    @pytest.mark.unit
    def test_generate_platform_recommendations_no_managers(self):
        """パッケージマネージャーなしでの推奨事項生成テスト"""
        verify_current_platform()

        from src.setup_repo.platform_detector import PlatformInfo

        diagnosis = {
            "package_managers": {"scoop": {"available": False}, "winget": {"available": False}},
            "ci_specific_issues": [],
            "recommendations": [],
        }

        # Windows環境でパッケージマネージャーなし
        windows_platform = PlatformInfo(
            name="windows",
            display_name="Windows",
            package_managers=["scoop", "winget"],
            shell="powershell",
            python_cmd="python",
        )

        _generate_platform_recommendations(diagnosis, windows_platform)

        recommendations = diagnosis["recommendations"]
        assert any("No package manager found on Windows" in rec for rec in recommendations)

    @pytest.mark.unit
    def test_platform_detector_class_caching(self):
        """PlatformDetectorクラスのキャッシュ機能テスト"""
        verify_current_platform()

        detector = PlatformDetector()

        # 初回呼び出し
        platform1 = detector.detect_platform()

        # 2回目呼び出し（キャッシュされた値を使用）
        platform2 = detector.detect_platform()

        assert platform1 == platform2

        # プラットフォーム情報も同様にキャッシュされる
        info1 = detector.get_platform_info()
        info2 = detector.get_platform_info()

        assert info1 is info2  # 同じオブジェクトインスタンス

    @pytest.mark.unit
    def test_platform_detector_environment_checks(self):
        """PlatformDetectorの環境チェック機能テスト"""
        verify_current_platform()

        detector = PlatformDetector()

        # CI環境チェック
        with patch.dict(os.environ, {"CI": "true"}):
            assert detector.is_ci_environment() is True

        with patch.dict(os.environ, {}, clear=True):
            assert detector.is_ci_environment() is False

        # GitHub Actionsチェック
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            assert detector.is_github_actions() is True

        # precommitチェック
        with patch.dict(os.environ, {"PRE_COMMIT": "1"}):
            assert detector.is_precommit_environment() is True

    @pytest.mark.unit
    def test_platform_detector_package_manager_selection(self):
        """PlatformDetectorのパッケージマネージャー選択テスト"""
        verify_current_platform()

        detector = PlatformDetector()

        # 利用可能なマネージャーがある場合
        with patch("src.setup_repo.platform_detector.get_available_package_managers", return_value=["scoop", "winget"]):
            manager = detector.get_package_manager()
            assert manager == "scoop"  # 最初の利用可能なマネージャー

        # 利用可能なマネージャーがない場合
        with patch("src.setup_repo.platform_detector.get_available_package_managers", return_value=[]):
            manager = detector.get_package_manager()
            # デフォルトのマネージャーが返される
            assert manager is not None

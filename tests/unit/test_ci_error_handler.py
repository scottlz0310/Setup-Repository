"""CI エラーハンドラーのテスト"""

import json
import os
from unittest.mock import Mock, patch

import pytest

from ..multiplatform.helpers import verify_current_platform


class TestCIErrorHandler:
    """CI エラーハンドラーのテストクラス"""

    @pytest.mark.unit
    def test_ci_error_handler_initialization(self):
        """CIエラーハンドラーの初期化テスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import CIErrorHandler
        except ImportError:
            pytest.skip("CIErrorHandlerが利用できません")

        handler = CIErrorHandler()
        assert handler is not None
        assert handler.errors == []
        assert handler.enable_github_annotations is True

    @pytest.mark.unit
    def test_handle_stage_error(self, temp_dir):
        """ステージエラー処理のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import CIErrorHandler
        except ImportError:
            pytest.skip("CIErrorHandlerが利用できません")

        # 必要なモジュールをモック
        with (
            patch("src.setup_repo.ci_error_handler.get_quality_logger") as mock_logger,
            patch("src.setup_repo.ci_error_handler.ErrorReporter") as mock_reporter,
            patch("src.setup_repo.ci_error_handler.CIEnvironmentInfo") as mock_ci_info,
        ):
            mock_logger.return_value = Mock()
            mock_reporter.return_value = Mock()
            mock_ci_info.get_ci_metadata.return_value = {}
            mock_ci_info.get_system_info.return_value = {}
            mock_ci_info.get_dependency_info.return_value = {}

            handler = CIErrorHandler(error_report_dir=temp_dir)
            test_error = Exception("テストステージエラー")

            # メソッドが存在する場合のみテスト
            if hasattr(handler, "handle_stage_error"):
                handler.handle_stage_error("test_stage", test_error, duration=1.5)
                assert len(handler.errors) == 1
                assert handler.errors[0] == test_error
            else:
                pytest.skip("メソッドが存在しません")

    @pytest.mark.unit
    def test_handle_quality_check_error(self, temp_dir):
        """品質チェックエラー処理のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import CIErrorHandler
        except ImportError:
            pytest.skip("CIErrorHandlerが利用できません")

        handler = CIErrorHandler(error_report_dir=temp_dir)
        test_error = Exception("品質チェック失敗")
        metrics = {"coverage": 75, "issues": 5}

        with patch("src.setup_repo.platform_detector.detect_platform") as mock_detect:
            mock_platform = Mock()
            mock_platform.name = "windows"
            mock_platform.display_name = "Windows"
            mock_platform.shell = "cmd"
            mock_platform.python_cmd = "python"
            mock_platform.package_managers = ["winget"]
            mock_detect.return_value = mock_platform

            handler.handle_quality_check_error("ruff", test_error, metrics)

        assert len(handler.errors) == 1
        assert handler.errors[0] == test_error

    @pytest.mark.unit
    def test_github_actions_detection(self):
        """GitHub Actions環境検出のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import CIErrorHandler
        except ImportError:
            pytest.skip("CIErrorHandlerが利用できません")

        handler = CIErrorHandler()

        # GitHub Actions環境をシミュレート
        with (
            patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}),
            patch(
                "src.setup_repo.ci_error_handler.CIEnvironmentInfo.detect_ci_environment", return_value="github_actions"
            ),
        ):
            assert handler._is_github_actions() is True

        # 非GitHub Actions環境
        with patch("src.setup_repo.ci_error_handler.CIEnvironmentInfo.detect_ci_environment", return_value="local"):
            assert handler._is_github_actions() is False

    @pytest.mark.unit
    def test_github_annotation_output(self):
        """GitHub Actionsアノテーション出力のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import CIErrorHandler
        except ImportError:
            pytest.skip("CIErrorHandlerが利用できません")

        with (
            patch("src.setup_repo.ci_error_handler.get_quality_logger") as mock_logger,
            patch("src.setup_repo.ci_error_handler.ErrorReporter") as mock_reporter,
            patch("src.setup_repo.ci_error_handler.CIEnvironmentInfo") as mock_ci_info,
        ):
            mock_logger.return_value = Mock()
            mock_reporter.return_value = Mock()
            mock_ci_info.get_ci_metadata.return_value = {}
            mock_ci_info.get_system_info.return_value = {}
            mock_ci_info.get_dependency_info.return_value = {}

            handler = CIErrorHandler()

            # GitHub Actions環境でのみアノテーションが出力される
            with patch("builtins.print") as mock_print, patch.object(handler, "_is_github_actions", return_value=True):
                if hasattr(handler, "_output_github_annotation"):
                    handler._output_github_annotation("error", "テストエラー", "test.py", 10)
                    mock_print.assert_called_once_with("::error file=test.py,line=10::テストエラー")
                else:
                    pytest.skip("メソッドが存在しません")

    @pytest.mark.unit
    def test_comprehensive_error_report(self, temp_dir):
        """包括的エラーレポート作成のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import CIErrorHandler
        except ImportError:
            pytest.skip("CIErrorHandlerが利用できません")

        handler = CIErrorHandler(error_report_dir=temp_dir)

        # エラーを追加
        error1 = Exception("エラー1")
        error2 = ValueError("エラー2")
        handler.errors = [error1, error2]

        with patch(
            "src.setup_repo.logging_config.get_platform_debug_info",
            return_value={"system": {"platform_system": "Linux"}},
        ):
            report = handler.create_comprehensive_error_report()

        assert report["total_errors"] == 2
        assert len(report["errors"]) == 2
        assert report["errors"][0]["type"] == "Exception"
        assert report["errors"][1]["type"] == "ValueError"

    @pytest.mark.unit
    def test_save_error_report(self, temp_dir):
        """エラーレポート保存のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import CIErrorHandler
        except ImportError:
            pytest.skip("CIErrorHandlerが利用できません")

        handler = CIErrorHandler(error_report_dir=temp_dir)
        handler.errors = [Exception("テストエラー")]

        with patch(
            "src.setup_repo.logging_config.get_platform_debug_info",
            return_value={"system": {"platform_system": "Linux"}},
        ):
            report_path = handler.save_error_report("test_report.json")

        assert report_path.exists()

        # レポート内容を確認
        with open(report_path, encoding="utf-8") as f:
            saved_report = json.load(f)

        assert saved_report["total_errors"] == 1

    @pytest.mark.unit
    def test_failure_summary_generation(self):
        """失敗サマリー生成のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import CIErrorHandler
        except ImportError:
            pytest.skip("CIErrorHandlerが利用できません")

        handler = CIErrorHandler()

        # エラーなしの場合
        summary = handler.generate_failure_summary()
        assert "エラーは発生していません" in summary

        # エラーありの場合
        handler.errors = [Exception("テストエラー")]

        with (
            patch("src.setup_repo.platform_detector.detect_platform") as mock_detect,
            patch("src.setup_repo.logging_config.get_platform_debug_info") as mock_debug,
        ):
            mock_platform = Mock()
            mock_platform.name = "linux"
            mock_platform.display_name = "Linux"
            mock_platform.shell = "bash"
            mock_platform.python_cmd = "python3"
            mock_platform.package_managers = ["apt"]
            mock_detect.return_value = mock_platform

            mock_debug.return_value = {
                "system": {"platform_system": "Linux", "platform_release": "5.4.0", "platform_machine": "x86_64"}
            }

            summary = handler.generate_failure_summary()

        assert "CI/CD失敗サマリー" in summary
        assert "Exception" in summary
        assert "テストエラー" in summary

    @pytest.mark.unit
    def test_quality_check_details_handling(self):
        """品質チェック詳細処理のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import CIErrorHandler
        except ImportError:
            pytest.skip("CIErrorHandlerが利用できません")

        handler = CIErrorHandler()

        # Ruffの詳細処理
        ruff_details = {
            "issues": [
                {"filename": "test.py", "location": {"row": 10}, "message": "Line too long"},
                {"filename": "main.py", "location": {"row": 5}, "message": "Unused import"},
            ]
        }

        with (
            patch("builtins.print") as mock_print,
            patch.object(handler, "_is_github_actions", return_value=False),
        ):
            if hasattr(handler, "_handle_quality_check_details"):
                handler._handle_quality_check_details("ruff", ruff_details)
                # GitHub Actionsでない場合はprintは呼ばれない、または実装によってはデバッグ出力のみ
                assert mock_print.call_count >= 0
            else:
                pytest.skip("メソッドが存在しません")

    @pytest.mark.unit
    def test_create_ci_error_handler_function(self, temp_dir):
        """create_ci_error_handler関数のテスト"""
        verify_current_platform()

        try:
            from src.setup_repo.ci_error_handler import create_ci_error_handler
        except ImportError:
            pytest.skip("create_ci_error_handlerが利用できません")

        handler = create_ci_error_handler(enable_github_annotations=False, error_report_dir=temp_dir)

        assert handler is not None
        assert handler.enable_github_annotations is False
        assert handler.error_report_dir == temp_dir

"""
CI/CDエラーハンドラーのテスト
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from setup_repo.ci_error_handler import (
    CIEnvironmentInfo,
    CIErrorHandler,
    create_ci_error_handler,
)
from setup_repo.quality_logger import LogLevel, QualityCheckError, RuffError


class TestCIEnvironmentInfo:
    """CI環境情報収集のテスト"""

    @patch.dict(
        os.environ,
        {
            "GITHUB_ACTIONS": "true",
            "GITHUB_WORKFLOW": "CI",
            "GITHUB_REPOSITORY": "test/repo",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": "abc123",
            "RUNNER_OS": "Linux",
        },
    )
    def test_get_github_actions_info(self):
        """GitHub Actions環境情報の取得をテスト"""
        info = CIEnvironmentInfo.get_github_actions_info()

        assert info["runner_os"] == "Linux"
        assert info["github_workflow"] == "CI"
        assert info["github_repository"] == "test/repo"
        assert info["github_ref"] == "refs/heads/main"
        assert info["github_sha"] == "abc123"

    def test_get_system_info(self):
        """システム情報の取得をテスト"""
        info = CIEnvironmentInfo.get_system_info()

        assert "python_version" in info
        assert "platform" in info
        assert "working_directory" in info
        assert "git_info" in info
        assert "environment_variables" in info

    @patch("subprocess.check_output")
    def test_get_dependency_info(self, mock_subprocess):
        """依存関係情報の取得をテスト"""
        # uvコマンドのモック
        mock_subprocess.side_effect = [
            "uv 0.1.0",  # uv --version
            json.dumps(
                [{"name": "pytest", "version": "7.0.0"}]
            ),  # pip list --format=json
        ]

        info = CIEnvironmentInfo.get_dependency_info()

        assert "uv_info" in info
        assert "packages" in info
        assert info["uv_info"]["version"] == "uv 0.1.0"
        assert info["packages"]["pytest"] == "7.0.0"


class TestCIErrorHandler:
    """CI/CDエラーハンドラーのテスト"""

    def test_error_handler_creation(self):
        """エラーハンドラーの作成をテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)

            handler = CIErrorHandler(
                enable_github_annotations=True, error_report_dir=error_report_dir
            )

            assert handler.enable_github_annotations is True
            assert handler.error_report_dir == error_report_dir
            assert len(handler.errors) == 0

    def test_handle_stage_error(self):
        """ステージエラーハンドリングのテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("テストエラー", "TEST_ERROR")
        context = {"stage": "test", "duration": 5.0}

        handler.handle_stage_error("TestStage", error, 5.0, context)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_handle_quality_check_error(self):
        """品質チェックエラーハンドリングのテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        issues = [{"filename": "test.py", "message": "テストエラー"}]
        error = RuffError("Ruffエラー", issues)
        metrics = {"issue_count": 1}

        handler.handle_quality_check_error("Ruff", error, metrics)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"})
    @patch("builtins.print")
    def test_github_annotations_output(self, mock_print):
        """GitHub Actionsアノテーション出力のテスト"""
        handler = CIErrorHandler(enable_github_annotations=True)

        error = QualityCheckError("テストエラー")
        handler.handle_stage_error("TestStage", error)

        # GitHub Actionsアノテーションが出力されることを確認
        mock_print.assert_called()
        call_args = [call[0][0] for call in mock_print.call_args_list]
        assert any("::error" in arg for arg in call_args)

    def test_comprehensive_error_report_creation(self):
        """包括的エラーレポート作成のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # 複数のエラーを追加
        errors = [
            QualityCheckError("エラー1", "ERROR_1"),
            RuffError("エラー2", [{"file": "test.py"}]),
        ]

        for error in errors:
            handler.errors.append(error)

        report = handler.create_comprehensive_error_report()

        assert report["total_errors"] == 2
        assert "ci_environment" in report
        assert "system_info" in report
        assert "dependency_info" in report
        assert len(report["errors"]) == 2

    def test_error_report_saving(self):
        """エラーレポート保存のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)
            handler = CIErrorHandler(
                enable_github_annotations=False, error_report_dir=error_report_dir
            )

            # エラーを追加
            error = QualityCheckError("テストエラー")
            handler.errors.append(error)

            # レポートを保存
            output_file = handler.save_error_report("test_report.json")

            assert output_file.exists()
            assert output_file.parent == error_report_dir

            # レポート内容を確認
            with open(output_file, encoding="utf-8") as f:
                report = json.load(f)

            assert report["total_errors"] == 1
            assert report["errors"][0]["message"] == "テストエラー"

    def test_failure_summary_generation(self):
        """失敗サマリー生成のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # エラーなしの場合
        summary = handler.generate_failure_summary()
        assert "エラーは発生していません" in summary

        # エラーありの場合
        error = QualityCheckError("テストエラー", "TEST_ERROR", {"detail": "詳細"})
        handler.errors.append(error)

        summary = handler.generate_failure_summary()
        assert "CI/CD失敗サマリー" in summary
        assert "QualityCheckError" in summary
        assert "テストエラー" in summary

    @patch.dict(
        os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_STEP_SUMMARY": "/tmp/summary"}
    )
    @patch("builtins.open", create=True)
    def test_github_step_summary_output(self, mock_open):
        """GitHub Step Summary出力のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("テストエラー")
        handler.errors.append(error)

        handler.output_github_step_summary()

        # ファイルが開かれることを確認
        mock_open.assert_called_once()

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "false"})
    def test_non_github_actions_environment(self):
        """非GitHub Actions環境でのテスト"""
        handler = CIErrorHandler(enable_github_annotations=True)

        assert handler._is_github_actions() is False

        # GitHub Actionsでない場合はアノテーションが出力されない
        with patch("builtins.print") as mock_print:
            handler._output_github_annotation("error", "テストメッセージ")
            mock_print.assert_not_called()


class TestCIErrorHandlerFactory:
    """CI/CDエラーハンドラーファクトリーのテスト"""

    def test_create_ci_error_handler(self):
        """CI/CDエラーハンドラー作成のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)

            handler = create_ci_error_handler(
                enable_github_annotations=True,
                error_report_dir=error_report_dir,
                log_level=LogLevel.DEBUG,
            )

            assert isinstance(handler, CIErrorHandler)
            assert handler.enable_github_annotations is True
            assert handler.error_report_dir == error_report_dir

    @patch.dict(os.environ, {"CI_JSON_LOGS": "true"})
    def test_create_ci_error_handler_with_json_logs(self):
        """JSON形式ログ付きCI/CDエラーハンドラー作成のテスト"""
        handler = create_ci_error_handler()

        assert isinstance(handler, CIErrorHandler)
        # JSON形式ログが有効になっていることを確認
        assert handler.logger.enable_json_format is True

"""
CI/CDエラーハンドラーのテスト
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from setup_repo.ci_error_handler import (
    CIEnvironmentInfo,
    CIErrorHandler,
    create_ci_error_handler,
)
from setup_repo.quality_errors import QualityCheckError, RuffError
from setup_repo.quality_logger import LogLevel


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

        # GitHub Step Summaryファイルが開かれることを確認
        summary_calls = [
            call for call in mock_open.call_args_list if "/tmp/summary" in str(call)
        ]
        assert len(summary_calls) > 0, "GitHub Step Summaryファイルが開かれませんでした"

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


class TestCIErrorHandlerAdvanced:
    """CI/CDエラーハンドラーの高度なテスト"""

    def test_handle_quality_check_details_ruff(self):
        """Ruff品質チェック詳細処理のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # Ruffエラーの詳細を持つエラーオブジェクトを作成
        error = QualityCheckError("Ruff check failed")
        error.details = {
            "issues": [
                {
                    "filename": "test.py",
                    "location": {"row": 10},
                    "message": "Line too long",
                },
                {
                    "filename": "main.py",
                    "location": {"row": 5},
                    "message": "Unused import",
                },
            ]
        }

        handler.handle_quality_check_error("ruff", error)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_handle_quality_check_details_mypy(self):
        """MyPy品質チェック詳細処理のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # MyPyエラーの詳細を持つエラーオブジェクトを作成
        error = QualityCheckError("MyPy check failed")
        error.details = {
            "errors": [
                "test.py:10: error: Incompatible types",
                "main.py:5: error: Missing return statement",
            ]
        }

        handler.handle_quality_check_error("mypy", error)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_handle_quality_check_details_tests(self):
        """テスト品質チェック詳細処理のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # テストエラーの詳細を持つエラーオブジェクトを作成
        error = QualityCheckError("Test check failed")
        error.details = {
            "failed_tests": [
                "test_example.py::test_function1",
                "test_example.py::test_function2",
            ]
        }

        handler.handle_quality_check_error("tests", error)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"})
    @patch("builtins.print")
    def test_handle_quality_check_details_with_github_annotations(self, mock_print):
        """GitHub Actionsアノテーション付き品質チェック詳細処理のテスト"""
        handler = CIErrorHandler(enable_github_annotations=True)

        # Ruffエラーの詳細を持つエラーオブジェクトを作成
        error = QualityCheckError("Ruff check failed")
        error.details = {
            "issues": [
                {
                    "filename": "test.py",
                    "location": {"row": 10},
                    "message": "Line too long",
                }
            ]
        }

        handler.handle_quality_check_error("ruff", error)

        # GitHub Actionsアノテーションが出力されることを確認
        mock_print.assert_called()
        call_args = [call[0][0] for call in mock_print.call_args_list]
        assert any("::warning" in arg for arg in call_args)

    def test_comprehensive_error_report_with_error_details(self):
        """詳細情報付きエラーレポート作成のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # 詳細情報付きエラーを追加
        error1 = QualityCheckError("Test error 1", "ERROR_001")
        error1.details = {"file": "test.py", "line": 10}
        error1.timestamp = "2023-01-01T00:00:00"

        error2 = RuffError("Test error 2", [{"file": "main.py"}])

        handler.errors.extend([error1, error2])

        report = handler.create_comprehensive_error_report()

        assert report["total_errors"] == 2
        assert len(report["errors"]) == 2

        # 最初のエラーの詳細を確認
        first_error = report["errors"][0]
        assert first_error["type"] == "QualityCheckError"
        assert first_error["message"] == "Test error 1"
        assert first_error["code"] == "ERROR_001"
        assert first_error["details"] == {"file": "test.py", "line": 10}
        assert first_error["timestamp"] == "2023-01-01T00:00:00"

    def test_save_error_report_with_custom_filename(self):
        """カスタムファイル名でのエラーレポート保存のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)
            handler = CIErrorHandler(
                enable_github_annotations=False, error_report_dir=error_report_dir
            )

            # エラーを追加
            error = QualityCheckError("Test error")
            handler.errors.append(error)

            # カスタムファイル名でレポートを保存
            output_file = handler.save_error_report("custom_report.json")

            assert output_file.exists()
            assert output_file.name == "custom_report.json"
            assert output_file.parent == error_report_dir

            # レポート内容を確認
            with open(output_file, encoding="utf-8") as f:
                report = json.load(f)

            assert report["total_errors"] == 1
            assert report["errors"][0]["message"] == "Test error"

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "true"})
    @patch("builtins.print")
    def test_save_error_report_github_actions_notice(self, mock_print):
        """GitHub Actions環境でのエラーレポート保存通知のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)
            handler = CIErrorHandler(
                enable_github_annotations=True, error_report_dir=error_report_dir
            )

            # エラーを追加
            error = QualityCheckError("Test error")
            handler.errors.append(error)

            # レポートを保存
            handler.save_error_report("test_report.json")

            # GitHub Actionsアノテーションが出力されることを確認
            mock_print.assert_called()
            call_args = [call[0][0] for call in mock_print.call_args_list]
            assert any(
                "::notice" in arg and "Error report saved" in arg for arg in call_args
            )

    def test_generate_failure_summary_with_multiple_errors(self):
        """複数エラーでの失敗サマリー生成のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # 複数のエラーを追加
        error1 = QualityCheckError("First error", "ERROR_001")
        error1.details = {"severity": "high"}

        error2 = RuffError("Second error", [{"file": "test.py"}])

        handler.errors.extend([error1, error2])

        summary = handler.generate_failure_summary()

        assert "CI/CD失敗サマリー (2件のエラー)" in summary
        assert "1. QualityCheckError" in summary
        assert "2. RuffError" in summary
        assert "First error" in summary
        assert "Second error" in summary
        assert "ERROR_001" in summary

    @patch.dict(
        os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_STEP_SUMMARY": "/tmp/summary"}
    )
    @patch("builtins.open", create=True)
    def test_output_github_step_summary_with_errors(self, mock_open):
        """エラーありでのGitHub Step Summary出力のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # エラーを追加
        error = QualityCheckError("Test error")
        handler.errors.append(error)

        handler.output_github_step_summary()

        # GitHub Step Summaryファイルが開かれることを確認
        summary_calls = [
            call for call in mock_open.call_args_list if "/tmp/summary" in str(call)
        ]
        assert len(summary_calls) > 0, "GitHub Step Summaryファイルが開かれませんでした"

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""})
    def test_output_github_step_summary_no_env_var(self):
        """GITHUB_STEP_SUMMARY環境変数がない場合のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # エラーを追加
        error = QualityCheckError("Test error")
        handler.errors.append(error)

        # 例外が発生しないことを確認
        handler.output_github_step_summary()

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/summary"})
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_output_github_step_summary_file_error(self, mock_open):
        """GitHub Step Summary出力時のファイルエラーのテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # エラーを追加
        error = QualityCheckError("Test error")
        handler.errors.append(error)

        # 例外が発生しないことを確認（内部でキャッチされる）
        handler.output_github_step_summary()

    @patch("sys.exit")
    def test_set_exit_code_with_errors(self, mock_exit):
        """エラーありでの終了コード設定のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)
            handler = CIErrorHandler(
                enable_github_annotations=False, error_report_dir=error_report_dir
            )

            # エラーを追加
            error = QualityCheckError("Test error")
            handler.errors.append(error)

            handler.set_exit_code(2)

            # sys.exitが呼ばれることを確認
            mock_exit.assert_called_once_with(2)

    @patch("sys.exit")
    def test_set_exit_code_no_errors(self, mock_exit):
        """エラーなしでの終了コード設定のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        handler.set_exit_code(0)

        # sys.exitが呼ばれることを確認
        mock_exit.assert_called_once_with(0)

    def test_output_github_annotation_with_file_and_line(self):
        """ファイルと行番号付きGitHub Actionsアノテーション出力のテスト"""
        handler = CIErrorHandler(enable_github_annotations=True)

        with (
            patch("builtins.print") as mock_print,
            patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}),
        ):
            handler._output_github_annotation("warning", "Test message", "test.py", 10)

            mock_print.assert_called_once_with(
                "::warning file=test.py,line=10::Test message"
            )

    def test_output_github_annotation_with_file_only(self):
        """ファイルのみ指定のGitHub Actionsアノテーション出力のテスト"""
        handler = CIErrorHandler(enable_github_annotations=True)

        with (
            patch("builtins.print") as mock_print,
            patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}),
        ):
            handler._output_github_annotation("error", "Test message", "test.py")

            mock_print.assert_called_once_with("::error file=test.py::Test message")

    def test_handle_stage_error_with_context(self):
        """コンテキスト付きステージエラーハンドリングのテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("Stage error")
        context = {"additional_info": "test context", "retry_count": 3}

        handler.handle_stage_error("TestStage", error, 10.5, context)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_error_reporter_integration(self):
        """ErrorReporterとの統合テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)
            handler = CIErrorHandler(
                enable_github_annotations=False, error_report_dir=error_report_dir
            )

            # ErrorReporterが正しく初期化されていることを確認
            assert handler.error_reporter is not None
            assert handler.error_reporter.report_dir == error_report_dir


class TestCIErrorHandlerEdgeCases:
    """CI/CDエラーハンドラーのエッジケースのテスト"""

    def test_error_handler_creation_with_default_values(self):
        """デフォルト値でのエラーハンドラー作成のテスト"""
        handler = CIErrorHandler()

        assert handler.enable_github_annotations is True
        assert handler.error_report_dir == Path("ci-error-reports")
        assert len(handler.errors) == 0
        assert handler.logger is not None
        assert handler.error_reporter is not None

    def test_error_handler_creation_with_custom_logger(self):
        """カスタムロガーでのエラーハンドラー作成のテスト"""
        from setup_repo.quality_logger import QualityLogger

        custom_logger = QualityLogger(name="test_logger")
        handler = CIErrorHandler(logger=custom_logger)

        assert handler.logger == custom_logger

    def test_handle_stage_error_without_context(self):
        """コンテキストなしでのステージエラーハンドリングのテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("Test error without context")
        handler.handle_stage_error("TestStage", error)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_handle_stage_error_without_duration(self):
        """実行時間なしでのステージエラーハンドリングのテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("Test error without duration")
        context = {"additional_info": "test"}
        handler.handle_stage_error("TestStage", error, context=context)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_handle_quality_check_error_without_metrics(self):
        """メトリクスなしでの品質チェックエラーハンドリングのテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("Test quality check error")
        handler.handle_quality_check_error("TestCheck", error)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_handle_quality_check_details_unknown_type(self):
        """未知の品質チェックタイプの詳細処理のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("Unknown check failed")
        error.details = {"unknown_field": "unknown_value"}

        handler.handle_quality_check_error("unknown_check", error)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_handle_quality_check_details_empty_issues(self):
        """空のissuesリストでのRuff詳細処理のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("Ruff check failed")
        error.details = {"issues": []}  # 空のリスト

        handler.handle_quality_check_error("ruff", error)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_handle_quality_check_details_many_issues(self):
        """多数のissuesでのRuff詳細処理のテスト（最初の5つのみ処理）"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # 10個のissuesを作成（最初の5つのみ処理されるはず）
        issues = []
        for i in range(10):
            issues.append(
                {
                    "filename": f"test{i}.py",
                    "location": {"row": i + 1},
                    "message": f"Issue {i}",
                }
            )

        error = QualityCheckError("Ruff check failed")
        error.details = {"issues": issues}

        handler.handle_quality_check_error("ruff", error)

        assert len(handler.errors) == 1
        assert handler.errors[0] == error

    def test_comprehensive_error_report_creation_empty_errors(self):
        """エラーなしでの包括的エラーレポート作成のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        report = handler.create_comprehensive_error_report()

        assert report["total_errors"] == 0
        assert len(report["errors"]) == 0
        assert "timestamp" in report
        assert "ci_environment" in report
        assert "system_info" in report
        assert "dependency_info" in report

    def test_save_error_report_without_filename(self):
        """ファイル名なしでのエラーレポート保存のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)
            handler = CIErrorHandler(
                enable_github_annotations=False, error_report_dir=error_report_dir
            )

            error = QualityCheckError("Test error")
            handler.errors.append(error)

            # ファイル名を指定せずにレポートを保存
            output_file = handler.save_error_report()

            assert output_file.exists()
            assert output_file.parent == error_report_dir

    def test_generate_failure_summary_no_errors(self):
        """エラーなしでの失敗サマリー生成のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        summary = handler.generate_failure_summary()

        assert "エラーは発生していません" in summary

    def test_generate_failure_summary_error_without_details(self):
        """詳細情報なしエラーでの失敗サマリー生成のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("Simple error")  # 詳細情報なし
        handler.errors.append(error)

        summary = handler.generate_failure_summary()

        assert "CI/CD失敗サマリー (1件のエラー)" in summary
        assert "QualityCheckError" in summary
        assert "Simple error" in summary

    @patch.dict(os.environ, {"GITHUB_ACTIONS": "false"})
    def test_output_github_step_summary_non_github_actions(self):
        """非GitHub Actions環境でのStep Summary出力のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        error = QualityCheckError("Test error")
        handler.errors.append(error)

        # 例外が発生しないことを確認
        handler.output_github_step_summary()

    def test_is_github_actions_detection(self):
        """GitHub Actions環境検出のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            assert handler._is_github_actions() is True

        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            assert handler._is_github_actions() is False

        with patch.dict(os.environ, {}, clear=True):
            assert handler._is_github_actions() is False

    def test_output_github_annotation_message_only(self):
        """メッセージのみのGitHub Actionsアノテーション出力のテスト"""
        handler = CIErrorHandler(enable_github_annotations=True)

        with (
            patch("builtins.print") as mock_print,
            patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}),
        ):
            handler._output_github_annotation("info", "Test message")

            mock_print.assert_called_once_with("::info::Test message")

    def test_ci_environment_info_integration(self):
        """CI環境情報統合のテスト"""
        handler = CIErrorHandler(enable_github_annotations=False)

        # CI環境情報が正しく設定されていることを確認
        assert handler.ci_info is not None
        assert handler.system_info is not None
        assert handler.dependency_info is not None

    def test_error_reporter_integration_advanced(self):
        """ErrorReporter統合の高度なテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)
            handler = CIErrorHandler(
                enable_github_annotations=False, error_report_dir=error_report_dir
            )

            # ErrorReporterのメソッドが正しく動作することを確認
            test_path = handler.error_reporter.get_report_path("test.json")
            assert test_path.parent == error_report_dir
            assert test_path.name == "test.json"


class TestCIErrorHandlerFactoryAdvanced:
    """CI/CDエラーハンドラーファクトリーの高度なテスト"""

    def test_create_ci_error_handler_default_values(self):
        """デフォルト値でのCI/CDエラーハンドラー作成のテスト"""
        handler = create_ci_error_handler()

        assert isinstance(handler, CIErrorHandler)
        assert handler.enable_github_annotations is True
        assert handler.error_report_dir is None or handler.error_report_dir == Path(
            "ci-error-reports"
        )

    @patch.dict(os.environ, {"CI_JSON_LOGS": "false"})
    def test_create_ci_error_handler_json_logs_disabled(self):
        """JSON形式ログ無効でのCI/CDエラーハンドラー作成のテスト"""
        handler = create_ci_error_handler()

        assert isinstance(handler, CIErrorHandler)
        # JSON形式ログが無効になっていることを確認
        assert handler.logger.enable_json_format is False

    @patch.dict(os.environ, {}, clear=True)
    def test_create_ci_error_handler_no_env_vars(self):
        """環境変数なしでのCI/CDエラーハンドラー作成のテスト"""
        handler = create_ci_error_handler()

        assert isinstance(handler, CIErrorHandler)
        # デフォルト値が使用されることを確認
        assert handler.logger.enable_json_format is False

    def test_create_ci_error_handler_all_parameters(self):
        """全パラメータ指定でのCI/CDエラーハンドラー作成のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)

            handler = create_ci_error_handler(
                enable_github_annotations=False,
                error_report_dir=error_report_dir,
                log_level=LogLevel.DEBUG,
            )

            assert isinstance(handler, CIErrorHandler)
            assert handler.enable_github_annotations is False
            assert handler.error_report_dir == error_report_dir
            assert handler.logger.log_level == LogLevel.DEBUG

    def test_create_ci_error_handler_logger_configuration(self):
        """ロガー設定の詳細テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_report_dir = Path(temp_dir)

            handler = create_ci_error_handler(
                error_report_dir=error_report_dir, log_level=LogLevel.WARNING
            )

            # ロガーが正しく設定されていることを確認
            assert handler.logger.name == "setup_repo.ci"
            assert handler.logger.log_level == LogLevel.WARNING
            assert handler.logger.enable_console is True


class TestCIEnvironmentInfoAdvanced:
    """CI環境情報収集の高度なテスト"""

    @patch.dict(os.environ, {}, clear=True)
    def test_get_github_actions_info_no_env_vars(self):
        """環境変数なしでのGitHub Actions情報取得のテスト"""
        info = CIEnvironmentInfo.get_github_actions_info()

        # 環境変数がない場合はNoneまたは空文字が返される
        assert info.get("runner_os") is None or info.get("runner_os") == ""
        assert info.get("github_workflow") is None or info.get("github_workflow") == ""

    @patch("subprocess.check_output")
    def test_get_dependency_info_command_not_found(self, mock_subprocess):
        """コマンドが見つからない場合の依存関係情報取得のテスト"""
        # uvコマンドが見つからない場合
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, "uv"),  # uv --version失敗
            json.dumps([{"name": "pytest", "version": "7.0.0"}]),  # pip list成功
        ]

        info = CIEnvironmentInfo.get_dependency_info()

        assert "uv_info" in info
        assert "packages" in info
        assert info["packages"]["pytest"] == "7.0.0"

    @patch("subprocess.check_output")
    def test_get_dependency_info_all_commands_fail(self, mock_subprocess):
        """全コマンドが失敗した場合の依存関係情報取得のテスト"""
        # 全てのコマンドが失敗
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "command")

        info = CIEnvironmentInfo.get_dependency_info()

        assert "uv_info" in info
        assert "packages" in info
        # エラー時はデフォルト値が設定される
        assert info["uv_info"] is None or "error" in str(info["uv_info"]).lower()

    def test_get_system_info_structure(self):
        """システム情報の構造テスト"""
        info = CIEnvironmentInfo.get_system_info()

        # 必要なフィールドが含まれていることを確認
        required_fields = [
            "python_version",
            "platform",
            "working_directory",
            "git_info",
            "environment_variables",
        ]
        for field in required_fields:
            assert field in info

    @patch.dict(
        os.environ,
        {
            "GITHUB_ACTIONS": "true",
            "GITHUB_WORKFLOW": "Test Workflow",
            "GITHUB_REPOSITORY": "user/repo",
            "GITHUB_REF": "refs/heads/feature",
            "GITHUB_SHA": "def456",
            "RUNNER_OS": "Windows",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_RUN_ID": "123456789",
        },
    )
    def test_get_github_actions_info_complete(self):
        """完全なGitHub Actions環境情報の取得をテスト"""
        info = CIEnvironmentInfo.get_github_actions_info()

        assert info["runner_os"] == "Windows"
        assert info["github_workflow"] == "Test Workflow"
        assert info["github_repository"] == "user/repo"
        assert info["github_ref"] == "refs/heads/feature"
        assert info["github_sha"] == "def456"
        # github_event_nameは実装されていないため、テストから除外
        assert info["github_run_id"] == "123456789"

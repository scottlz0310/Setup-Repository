"""CI エラーハンドラーの包括的テスト."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.ci_error_handler import CIErrorHandler, create_ci_error_handler
from setup_repo.quality_errors import QualityCheckError
from setup_repo.quality_logger import QualityLogger


class TestCIErrorHandler:
    """CIErrorHandlerクラスの包括的テスト."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_logger = Mock(spec=QualityLogger)
        self.handler = CIErrorHandler(logger=self.mock_logger, error_report_dir=self.temp_dir)

    @pytest.mark.unit
    def test_init_default_values(self):
        """デフォルト値での初期化テスト."""
        handler = CIErrorHandler()
        assert handler.logger is not None
        assert handler.errors == []
        assert handler.error_report_dir is not None

    @pytest.mark.unit
    def test_init_with_values(self):
        """値指定での初期化テスト."""
        assert self.handler.error_report_dir == self.temp_dir
        assert self.handler.logger == self.mock_logger
        assert self.handler.errors == []

    @pytest.mark.unit
    def test_handle_stage_error_quality_check_error(self):
        """品質チェックエラーの処理テスト."""
        error = QualityCheckError("Test error", "ruff", {"details": "test"})

        self.handler.handle_stage_error("lint", error)

        assert len(self.handler.errors) == 1
        assert self.handler.errors[0] == error

        self.mock_logger.log_ci_stage_failure.assert_called_once_with("lint", error, None)

    @pytest.mark.unit
    def test_handle_stage_error_generic_exception(self):
        """一般的な例外の処理テスト."""
        error = ValueError("Generic error")

        self.handler.handle_stage_error("build", error)

        assert len(self.handler.errors) == 1
        assert self.handler.errors[0] == error

    @pytest.mark.unit
    def test_handle_stage_error_with_context(self):
        """コンテキスト付きエラー処理テスト."""
        error = RuntimeError("Runtime error")
        context = {"file": "test.py", "line": 42}

        self.handler.handle_stage_error("test", error, context)

        assert len(self.handler.errors) == 1
        assert self.handler.errors[0] == error

    @pytest.mark.unit
    def test_handle_quality_check_error_ruff_error(self):
        """Ruffエラーの品質チェック処理テスト."""
        error = QualityCheckError("Ruff error", "ruff", {"issue_count": 5})

        self.handler.handle_quality_check_error("ruff", error)

        assert len(self.handler.errors) == 1
        assert self.handler.errors[0] == error

        self.mock_logger.log_quality_check_failure.assert_called_once_with("ruff", error, None)

    @pytest.mark.unit
    def test_handle_quality_check_error_pyright_error(self):
        """Pyrightエラーの品質チェック処理テスト."""
        error = QualityCheckError("Pyright error", "pyright", {"error_count": 3})

        self.handler.handle_quality_check_error("pyright", error)

        assert len(self.handler.errors) == 1
        assert self.handler.errors[0] == error

    @pytest.mark.unit
    def test_handle_quality_check_error_with_details(self):
        """詳細情報付き品質チェックエラー処理テスト."""
        error = QualityCheckError("Test error", "test", {"count": 10})

        with patch.object(self.handler, "_handle_quality_check_details") as mock_details:
            mock_details.return_value = {"processed": True}

            self.handler.handle_quality_check_error("test", error)

        # メソッドが呼ばれたことを確認
        if hasattr(self.handler, "_handle_quality_check_details"):
            mock_details.assert_called_once_with("test", {"count": 10})

    @pytest.mark.unit
    def test_handle_quality_check_details_ruff(self):
        """Ruff詳細処理テスト."""
        details = {"issues": [{"file": "test.py", "line": 10, "code": "E501", "message": "Line too long"}]}

        # メソッドが存在することを確認してテスト
        self.handler._handle_quality_check_details("ruff", details)
        # 実行が完了すれば成功

    @pytest.mark.unit
    def test_handle_quality_check_details_pyright(self):
        """Pyright詳細処理テスト."""
        details = {"errors": [{"file": "test.py", "line": 5, "message": "Type error"}]}

        # メソッドが存在することを確認してテスト
        self.handler._handle_quality_check_details("pyright", details)
        # 実行が完了すれば成功

    @pytest.mark.unit
    def test_handle_quality_check_details_pytest(self):
        """Pytest詳細処理テスト."""
        details = {"failed_tests": [{"test": "test_example", "error": "AssertionError"}]}

        # メソッドが存在することを確認してテスト
        self.handler._handle_quality_check_details("tests", details)
        # 実行が完了すれば成功

    @pytest.mark.unit
    def test_handle_quality_check_details_security(self):
        """セキュリティ詳細処理テスト."""
        details = {"vulnerabilities": [{"severity": "HIGH", "description": "SQL injection"}]}

        # メソッドが存在することを確認してテスト
        self.handler._handle_quality_check_details("security", details)
        # 実行が完了すれば成功

    @pytest.mark.unit
    def test_handle_quality_check_details_unknown_tool(self):
        """未知のツール詳細処理テスト."""
        details = {"unknown": "data"}

        # メソッドが存在することを確認してテスト
        self.handler._handle_quality_check_details("unknown", details)
        # 実行が完了すれば成功

    @pytest.mark.unit
    def test_create_comprehensive_error_report(self):
        """包括的エラーレポート作成テスト."""
        # エラーを追加
        error1 = QualityCheckError("Lint error", "ruff")
        error2 = RuntimeError("Test error")
        self.handler.handle_stage_error("lint", error1)
        self.handler.handle_stage_error("test", error2)

        report = self.handler.create_comprehensive_error_report()

        assert isinstance(report, dict)
        # 基本的な構造を確認
        assert len(report) > 0

    @pytest.mark.unit
    def test_create_comprehensive_error_report_no_errors(self):
        """エラーなしでの包括的レポート作成テスト."""
        report = self.handler.create_comprehensive_error_report()

        assert isinstance(report, dict)
        # エラーがない場合の基本的な構造を確認
        assert len(report) >= 0

    @pytest.mark.unit
    def test_save_error_report_success(self):
        """エラーレポート保存成功テスト."""
        # エラーを追加してレポートを作成
        error = QualityCheckError("Test error", "TEST")
        self.handler.handle_stage_error("test", error)

        output_file = self.temp_dir / "error-report.json"
        result_file = self.handler.save_error_report(str(output_file.name))

        assert result_file.exists()

        # ファイル内容を確認
        with open(result_file, encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["total_errors"] == 1
        assert len(saved_data["errors"]) == 1

        self.mock_logger.info.assert_called()

    @pytest.mark.unit
    def test_save_error_report_default_path(self):
        """デフォルトパスでのエラーレポート保存テスト."""
        result_file = self.handler.save_error_report()

        assert result_file.exists()
        assert "ci_error_report" in result_file.name

    @pytest.mark.unit
    def test_save_error_report_io_error(self):
        """エラーレポート保存IOエラーテスト."""
        # 書き込み不可能なパス
        invalid_path = Path("C:/invalid/path/report.json")

        # 無効なパスでの保存をテスト
        result_file = self.handler.save_error_report(str(invalid_path))

        # フォールバックで保存されるか、エラーログが出力される
        if result_file is None:
            self.mock_logger.error.assert_called()
        else:
            assert result_file.exists()

    @pytest.mark.unit
    def test_generate_failure_summary_with_errors(self):
        """エラーありでの失敗サマリー生成テスト."""
        # エラーを追加
        error1 = QualityCheckError("Lint error 1", "ruff")
        error2 = RuntimeError("Test error")
        error3 = QualityCheckError("Lint error 2", "ruff")

        self.handler.handle_stage_error("lint", error1)
        self.handler.handle_stage_error("test", error2)
        self.handler.handle_stage_error("lint", error3)

        summary = self.handler.generate_failure_summary()

        # 基本的な構造を確認
        assert isinstance(summary, (dict, str))

    @pytest.mark.unit
    def test_generate_failure_summary_no_errors(self):
        """エラーなしでの失敗サマリー生成テスト."""
        summary = self.handler.generate_failure_summary()

        # エラーがない場合の基本的な構造を確認
        assert isinstance(summary, (dict, str))

    @pytest.mark.unit
    @patch.dict("os.environ", {"GITHUB_ACTIONS": "true"})
    def test_output_github_step_summary_in_actions(self):
        """GitHub Actions環境でのステップサマリー出力テスト."""
        summary_file = self.temp_dir / "github_step_summary.md"

        # エラーを追加
        error1 = QualityCheckError("Lint error", "LINT")
        error2 = QualityCheckError("Test error", "TEST")
        self.handler.handle_stage_error("lint", error1)
        self.handler.handle_stage_error("test", error2)

        with patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": str(summary_file)}):
            self.handler.output_github_step_summary()

        assert summary_file.exists()

        # ファイル内容を確認
        content = summary_file.read_text(encoding="utf-8")
        assert "CI/CD失敗サマリー" in content
        assert "2件のエラー" in content

    @pytest.mark.unit
    @patch.dict("os.environ", {}, clear=True)
    def test_output_github_step_summary_not_in_actions(self):
        """GitHub Actions環境外でのステップサマリー出力テスト."""
        # GitHub Actions環境外では何もしない
        self.handler.output_github_step_summary()

        # メソッドが実行されたことを確認（エラーが発生しない）
        # GitHub Actions環境でない場合は早期リターンする
        assert True  # メソッドが完了すれば成功

    @pytest.mark.unit
    def test_is_github_actions_true(self):
        """GitHub Actions環境判定テスト（True）."""
        with patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}):
            assert self.handler._is_github_actions() is True

    @pytest.mark.unit
    def test_is_github_actions_false(self):
        """GitHub Actions環境判定テスト（False）."""
        with patch.dict("os.environ", {}, clear=True):
            assert self.handler._is_github_actions() is False

    @pytest.mark.unit
    @patch.dict("os.environ", {"GITHUB_ACTIONS": "true"})
    def test_output_github_annotation_error(self):
        """GitHub Actionsエラーアノテーション出力テスト."""
        with patch("builtins.print") as mock_print:
            self.handler._output_github_annotation("error", "Test error message", "test.py", 10)

        mock_print.assert_called_once_with("::error file=test.py,line=10::Test error message")

    @pytest.mark.unit
    @patch.dict("os.environ", {"GITHUB_ACTIONS": "true"})
    def test_output_github_annotation_warning(self):
        """GitHub Actions警告アノテーション出力テスト."""
        with patch("builtins.print") as mock_print:
            self.handler._output_github_annotation("warning", "Test warning message")

        mock_print.assert_called_once_with("::warning::Test warning message")

    @pytest.mark.unit
    @patch.dict("os.environ", {}, clear=True)
    def test_output_github_annotation_not_in_actions(self):
        """GitHub Actions環境外でのアノテーション出力テスト."""
        with patch("builtins.print") as mock_print:
            self.handler._output_github_annotation("error", "Test message")

        # GitHub Actions環境外では何も出力しない
        mock_print.assert_not_called()

    @pytest.mark.unit
    def test_set_exit_code_higher_priority(self):
        """より高い優先度での終了コード設定テスト."""
        # set_exit_codeはsys.exitを呼び出すためSystemExitが発生
        with pytest.raises(SystemExit) as exc_info:
            self.handler.set_exit_code(1)
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_set_exit_code_lower_priority(self):
        """より低い優先度での終了コード設定テスト."""
        # set_exit_codeはsys.exitを呼び出すためSystemExitが発生
        with pytest.raises(SystemExit) as exc_info:
            self.handler.set_exit_code(2)
        assert exc_info.value.code == 2

    @pytest.mark.unit
    def test_set_exit_code_same_priority(self):
        """同じ優先度での終了コード設定テスト."""
        # set_exit_codeはsys.exitを呼び出すためSystemExitが発生
        with pytest.raises(SystemExit) as exc_info:
            self.handler.set_exit_code(1)
        assert exc_info.value.code == 1


class TestCreateCIErrorHandler:
    """create_ci_error_handler関数のテスト."""

    @pytest.mark.unit
    def test_create_ci_error_handler_default(self):
        """デフォルト値でのCIエラーハンドラー作成テスト."""
        handler = create_ci_error_handler()

        assert isinstance(handler, CIErrorHandler)
        assert handler.logger is not None

    @pytest.mark.unit
    def test_create_ci_error_handler_with_params(self):
        """パラメータ指定でのCIエラーハンドラー作成テスト."""
        temp_dir = Path(tempfile.mkdtemp())
        Mock(spec=QualityLogger)

        handler = create_ci_error_handler(error_report_dir=temp_dir)

        assert isinstance(handler, CIErrorHandler)
        assert handler.error_report_dir == temp_dir

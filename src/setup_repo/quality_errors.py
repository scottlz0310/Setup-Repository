"""
品質チェック専用のエラークラスとエラーハンドリング機能

このモジュールは、品質チェック、CI/CD、テスト実行に関する
エラークラスとエラーハンドリング機能を提供します。
"""

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


class QualityCheckError(Exception):
    """品質チェック関連のベースエラークラス"""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "QUALITY_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class RuffError(QualityCheckError):
    """Ruffリンティングエラー"""

    def __init__(self, message: str, issues: list[dict[str, Any]] | None = None):
        super().__init__(message, "RUFF_ERROR", {"issues": issues or []})


class MyPyError(QualityCheckError):
    """MyPy型チェックエラー"""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message, "MYPY_ERROR", {"errors": errors or []})


class PyrightError(QualityCheckError):
    """Pyright/BasedPyright 型チェックエラー"""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message, "PYRIGHT_ERROR", {"errors": errors or []})


class TestFailureError(QualityCheckError):
    """テスト失敗エラー"""

    def __init__(
        self,
        message: str,
        failed_tests: list[str] | None = None,
        coverage: float | None = None,
    ):
        super().__init__(
            message,
            "TEST_FAILURE",
            {"failed_tests": failed_tests or [], "coverage": coverage},
        )


class CoverageError(QualityCheckError):
    """カバレッジ不足エラー"""

    def __init__(self, message: str, current_coverage: float, required_coverage: float):
        super().__init__(
            message,
            "COVERAGE_ERROR",
            {
                "current_coverage": current_coverage,
                "required_coverage": required_coverage,
            },
        )


class SecurityScanError(QualityCheckError):
    """セキュリティスキャンエラー"""

    def __init__(self, message: str, vulnerabilities: list[dict[str, Any]] | None = None):
        super().__init__(message, "SECURITY_ERROR", {"vulnerabilities": vulnerabilities or []})


class CIError(Exception):
    """CI/CD関連のベースエラークラス"""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "CI_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class ReleaseError(CIError):
    """リリースプロセスエラー"""

    def __init__(self, message: str, release_stage: str | None = None):
        super().__init__(message, "RELEASE_ERROR", {"release_stage": release_stage})


class ErrorReporter:
    """統一されたエラーレポート機能を提供するクラス"""

    def __init__(self, report_dir: Path | None = None):
        self.report_dir = report_dir or Path("error-reports")

    def save_report(self, error_data: dict[str, Any], report_type: str) -> Path:
        """エラーレポートを保存する統一インターフェース"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_error_report_{timestamp}.json"
        from .security_helpers import validate_file_path

        output_file = self.get_report_path(filename)

        # ファイルパスの安全性を検証
        if not validate_file_path(output_file, [".json", ".txt"]):
            raise ValueError(f"Unsafe file path detected: {output_file}")

        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)

            return output_file
        except (OSError, PermissionError) as e:
            # ファイル操作エラーまたは権限エラーの場合、一時ディレクトリを使用
            import tempfile

            temp_file = Path(tempfile.gettempdir()) / filename
            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(error_data, f, indent=2, ensure_ascii=False)
                return temp_file
            except (TypeError, ValueError) as json_error:
                # JSONエンコードエラーの場合、テキストファイルとして保存
                text_file = temp_file.with_suffix(".txt")
                with open(text_file, "w", encoding="utf-8") as f:
                    f.write(f"JSONエンコードエラー: {json_error}\n")
                    f.write(f"元のエラー: {e}\n")
                    f.write(f"エラーデータ: {str(error_data)}\n")
                return text_file
        except (TypeError, ValueError) as e:
            # JSONエンコードエラーの場合、テキストファイルとして保存
            text_file = output_file.with_suffix(".txt")
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(f"JSONエンコードエラー: {e}\n")
                f.write(f"エラーデータ: {str(error_data)}\n")
            return text_file

    def get_report_path(self, filename: str) -> Path:
        """レポートファイルのパスを取得"""
        from .security_helpers import safe_path_join

        return safe_path_join(self.report_dir, filename)

    def create_error_report(self, errors: list[Exception], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """詳細なエラーレポートを作成"""
        report: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "total_errors": len(errors),
            "context": context or {},
            "errors": [],
        }

        for error in errors:
            error_entry = {
                "type": type(error).__name__,
                "message": str(error),
                "timestamp": getattr(error, "timestamp", datetime.now().isoformat()),
            }

            if hasattr(error, "error_code"):
                error_entry["code"] = error.error_code

            if hasattr(error, "details"):
                error_entry["details"] = error.details

            report["errors"].append(error_entry)

        return report

    def format_error_message(self, error: Exception) -> str:
        """エラーメッセージをフォーマット"""
        if isinstance(error, (QualityCheckError, CIError)):
            message = f"[{error.error_code}] {error.message}"
            if error.details:
                message += f" - 詳細: {error.details}"
            return message
        else:
            return str(error)

    def log_exception(self, error: Exception, include_traceback: bool = True) -> str:
        """例外情報をログ用にフォーマット"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
        }

        if hasattr(error, "error_code"):
            error_info["error_code"] = error.error_code

        if hasattr(error, "details"):
            error_info["error_details"] = error.details

        from .security_helpers import safe_html_escape

        # JSONダンプ前にHTMLエスケープを適用
        escaped_error_info = {
            key: safe_html_escape(value) if isinstance(value, str) else value for key, value in error_info.items()
        }

        formatted_error = json.dumps(escaped_error_info, ensure_ascii=False, indent=2)

        if include_traceback:
            formatted_error += f"\nスタックトレース: {traceback.format_exc()}"

        return formatted_error

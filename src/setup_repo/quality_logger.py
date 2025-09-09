"""
品質チェック専用のロガーとエラーハンドリングクラス

このモジュールは、品質チェック、CI/CD、テスト実行に関する
包括的なロギングとエラーハンドリング機能を提供します。
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class LogLevel(Enum):
    """ログレベル定義"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class QualityCheckError(Exception):
    """品質チェック関連のベースエラークラス"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "QUALITY_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class RuffError(QualityCheckError):
    """Ruffリンティングエラー"""

    def __init__(self, message: str, issues: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message, "RUFF_ERROR", {"issues": issues or []})


class MyPyError(QualityCheckError):
    """MyPy型チェックエラー"""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message, "MYPY_ERROR", {"errors": errors or []})


class TestFailureError(QualityCheckError):
    """テスト失敗エラー"""

    def __init__(
        self,
        message: str,
        failed_tests: Optional[List[str]] = None,
        coverage: Optional[float] = None,
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

    def __init__(
        self, message: str, vulnerabilities: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            message, "SECURITY_ERROR", {"vulnerabilities": vulnerabilities or []}
        )


class CIError(Exception):
    """CI/CD関連のベースエラークラス"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "CI_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class ReleaseError(CIError):
    """リリースプロセスエラー"""

    def __init__(self, message: str, release_stage: Optional[str] = None):
        super().__init__(message, "RELEASE_ERROR", {"release_stage": release_stage})


class QualityLogger:
    """品質チェック専用の包括的ロガークラス"""

    def __init__(
        self,
        name: str = "setup_repo.quality",
        log_level: LogLevel = LogLevel.INFO,
        log_file: Optional[Path] = None,
        enable_console: bool = True,
        enable_json_format: bool = False,
    ):
        """
        品質ロガーを初期化

        Args:
            name: ロガー名
            log_level: ログレベル
            log_file: ログファイルパス（Noneの場合はファイル出力なし）
            enable_console: コンソール出力を有効にするか
            enable_json_format: JSON形式でログを出力するか
        """
        self.name = name
        self.log_level = log_level
        self.log_file = log_file
        self.enable_console = enable_console
        self.enable_json_format = enable_json_format

        # ロガーを設定
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.value))

        # 既存のハンドラーをクリア
        self.logger.handlers.clear()

        # コンソールハンドラーを追加
        if enable_console:
            self._setup_console_handler()

        # ファイルハンドラーを追加
        if log_file:
            self._setup_file_handler()

    def _setup_console_handler(self) -> None:
        """コンソールハンドラーを設定"""
        console_handler = logging.StreamHandler(sys.stdout)

        if self.enable_json_format:
            formatter = self._create_json_formatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _setup_file_handler(self) -> None:
        """ファイルハンドラーを設定"""
        if not self.log_file:
            return

        # ログディレクトリを作成
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")

        if self.enable_json_format:
            formatter = self._create_json_formatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def _create_json_formatter(self) -> logging.Formatter:
        """JSON形式のフォーマッターを作成"""

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_entry, ensure_ascii=False)

        return JsonFormatter()

    def debug(self, message: str, **kwargs) -> None:
        """デバッグレベルのログ"""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs) -> None:
        """情報レベルのログ"""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """警告レベルのログ"""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs) -> None:
        """エラーレベルのログ"""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """重大エラーレベルのログ"""
        self.logger.critical(message, extra=kwargs)

    def log_quality_check_start(
        self, check_type: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """品質チェック開始をログ"""
        message = f"品質チェック開始: {check_type}"
        if details:
            message += f" - 詳細: {details}"
        self.info(message)

    def log_quality_check_success(
        self, check_type: str, metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """品質チェック成功をログ"""
        message = f"品質チェック成功: {check_type}"
        if metrics:
            message += f" - メトリクス: {metrics}"
        self.info(message)

    def log_quality_check_failure(
        self,
        check_type: str,
        error: Union[Exception, str],
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """品質チェック失敗をログ"""
        if isinstance(error, Exception):
            message = f"品質チェック失敗: {check_type} - {str(error)}"
            if hasattr(error, "details"):
                details = {**(details or {}), **error.details}
        else:
            message = f"品質チェック失敗: {check_type} - {error}"

        if details:
            message += f" - 詳細: {details}"

        self.error(message)

        # 例外の場合はスタックトレースも記録
        if isinstance(error, Exception):
            self.debug(f"スタックトレース: {traceback.format_exc()}")

    def log_quality_check_result(self, check_type: str, result: Dict[str, Any]) -> None:
        """品質チェック結果をログ"""
        if result.get("success", False):
            self.log_quality_check_success(check_type, result.get("metrics"))
        else:
            errors = result.get("errors", [])
            error_message = "; ".join(errors) if errors else "不明なエラー"
            self.log_quality_check_failure(
                check_type, error_message, result.get("details")
            )

    def log_metrics_summary(self, metrics: Union[Dict[str, Any], Any]) -> None:
        """メトリクス概要をログ"""
        self.info("=== 品質メトリクス概要 ===")

        # QualityMetricsオブジェクトの場合は辞書に変換
        if hasattr(metrics, "__dict__"):
            metrics_dict = metrics.__dict__
        elif hasattr(metrics, "items"):
            metrics_dict = metrics
        else:
            # dataclassの場合
            try:
                from dataclasses import asdict

                metrics_dict = asdict(metrics)
            except (ImportError, TypeError):
                self.warning(f"メトリクスの形式が不正です: {type(metrics)}")
                return

        for key, value in metrics_dict.items():
            if isinstance(value, (int, float)):
                self.info(f"{key}: {value}")
            elif isinstance(value, bool):
                status = "✅" if value else "❌"
                self.info(f"{key}: {status}")
            else:
                self.info(f"{key}: {value}")

    def log_ci_stage_start(
        self, stage: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """CI/CDステージ開始をログ"""
        message = f"CI/CDステージ開始: {stage}"
        if details:
            message += f" - 詳細: {details}"
        self.info(message)

    def log_ci_stage_success(
        self, stage: str, duration: Optional[float] = None
    ) -> None:
        """CI/CDステージ成功をログ"""
        message = f"CI/CDステージ成功: {stage}"
        if duration:
            message += f" - 実行時間: {duration:.2f}秒"
        self.info(message)

    def log_ci_stage_failure(
        self, stage: str, error: Union[Exception, str], duration: Optional[float] = None
    ) -> None:
        """CI/CDステージ失敗をログ"""
        message = f"CI/CDステージ失敗: {stage} - {str(error)}"
        if duration:
            message += f" - 実行時間: {duration:.2f}秒"

        self.error(message)

        # 例外の場合はスタックトレースも記録
        if isinstance(error, Exception):
            self.debug(f"スタックトレース: {traceback.format_exc()}")

    def log_error_with_context(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        include_traceback: bool = True,
    ) -> None:
        """コンテキスト付きエラーログ"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
        }

        if hasattr(error, "error_code"):
            error_info["error_code"] = error.error_code

        if hasattr(error, "details"):
            error_info["error_details"] = error.details

        if context:
            error_info["context"] = context

        self.error(
            f"エラー発生: {json.dumps(error_info, ensure_ascii=False, indent=2)}"
        )

        if include_traceback:
            self.debug(f"スタックトレース: {traceback.format_exc()}")

    def create_error_report(
        self, errors: List[Exception], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """詳細なエラーレポートを作成"""
        report = {
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

    def save_error_report(
        self,
        errors: List[Exception],
        output_file: Path,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """エラーレポートをファイルに保存"""
        report = self.create_error_report(errors, context)

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.info(f"エラーレポートを保存しました: {output_file}")


# グローバルロガーインスタンス
_default_logger: Optional[QualityLogger] = None


def get_quality_logger(
    name: str = "setup_repo.quality",
    log_level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None,
    enable_console: bool = True,
    enable_json_format: bool = False,
) -> QualityLogger:
    """品質ロガーのシングルトンインスタンスを取得"""
    global _default_logger

    if _default_logger is None:
        _default_logger = QualityLogger(
            name=name,
            log_level=log_level,
            log_file=log_file,
            enable_console=enable_console,
            enable_json_format=enable_json_format,
        )

    return _default_logger


def configure_quality_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_file: Optional[Path] = None,
    enable_console: bool = True,
    enable_json_format: bool = False,
) -> QualityLogger:
    """品質ロギングを設定"""
    global _default_logger

    _default_logger = QualityLogger(
        log_level=log_level,
        log_file=log_file,
        enable_console=enable_console,
        enable_json_format=enable_json_format,
    )

    return _default_logger

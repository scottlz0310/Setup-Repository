"""
品質チェック専用のロガー機能

このモジュールは、品質チェック、CI/CD、テスト実行に関する
基本的なロギング機能を提供します。
"""

import logging
import sys
import traceback
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

# 分割されたモジュールからインポート
from .quality_errors import (
    CIError,
    CoverageError,
    ErrorReporter,
    MyPyError,
    QualityCheckError,
    ReleaseError,
    RuffError,
    SecurityScanError,
    TestFailureError,
)
from .quality_formatters import (
    ColoredFormatter,
    JSONFormatter,
    format_metrics_summary,
)


class LogLevel(Enum):
    """ログレベル定義"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


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
        return JSONFormatter()

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
        self, check_type: str, details: Optional[dict[str, Any]] = None
    ) -> None:
        """品質チェック開始をログ"""
        message = f"品質チェック開始: {check_type}"
        if details:
            message += f" - 詳細: {details}"
        self.info(message)

    def log_quality_check_success(
        self, check_type: str, metrics: Optional[dict[str, Any]] = None
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
        details: Optional[dict[str, Any]] = None,
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

    def log_quality_check_result(self, check_type: str, result: dict[str, Any]) -> None:
        """品質チェック結果をログ"""
        if result.get("success", False):
            self.log_quality_check_success(check_type, result.get("metrics"))
        else:
            errors = result.get("errors", [])
            error_message = "; ".join(errors) if errors else "不明なエラー"
            self.log_quality_check_failure(
                check_type, error_message, result.get("details")
            )

    def log_metrics_summary(self, metrics: Union[dict[str, Any], Any]) -> None:
        """メトリクス概要をログ"""
        # QualityMetricsオブジェクトの場合は辞書に変換
        if hasattr(metrics, "__dict__"):
            metrics_dict = metrics.__dict__
        elif hasattr(metrics, "items"):
            metrics_dict = metrics
        else:
            # dataclassの場合
            try:
                from dataclasses import asdict, is_dataclass

                if is_dataclass(metrics) and not isinstance(metrics, type):
                    metrics_dict = asdict(metrics)
                else:
                    self.warning(f"メトリクスの形式が不正です: {type(metrics)}")
                    return
            except (ImportError, TypeError):
                self.warning(f"メトリクスの形式が不正です: {type(metrics)}")
                return

        formatted_summary = format_metrics_summary(metrics_dict)
        self.info(formatted_summary)

    def log_ci_stage_start(
        self, stage: str, details: Optional[dict[str, Any]] = None
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
        context: Optional[dict[str, Any]] = None,
        include_traceback: bool = True,
    ) -> None:
        """コンテキスト付きエラーログ"""
        error_reporter = ErrorReporter()
        formatted_error = error_reporter.log_exception(error, include_traceback)

        if context:
            formatted_error += f"\nコンテキスト: {context}"

        self.error(f"エラー発生: {formatted_error}")

    def create_error_report(
        self, errors: list[Exception], context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """詳細なエラーレポートを作成"""
        error_reporter = ErrorReporter()
        return error_reporter.create_error_report(errors, context)

    def save_error_report(
        self,
        errors: list[Exception],
        output_file: Optional[Path] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> Path:
        """エラーレポートをファイルに保存"""
        error_reporter = ErrorReporter()
        report = error_reporter.create_error_report(errors, context)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                import json

                json.dump(report, f, indent=2, ensure_ascii=False)

            self.info(f"エラーレポートを保存しました: {output_file}")
            return output_file
        else:
            # ErrorReporterを使用して統一されたレポート保存
            saved_path = error_reporter.save_report(report, "quality")
            self.info(f"エラーレポートを保存しました: {saved_path}")
            return saved_path


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


# 後方互換性のためのエイリアス
# 既存のインポートパスを維持するため、分割されたモジュールの機能をここで再エクスポート
__all__ = [
    "LogLevel",
    "QualityLogger",
    "get_quality_logger",
    "configure_quality_logging",
    # エラークラス（後方互換性）
    "QualityCheckError",
    "RuffError",
    "MyPyError",
    "TestFailureError",
    "CoverageError",
    "SecurityScanError",
    "CIError",
    "ReleaseError",
    "ErrorReporter",
    # フォーマッター（後方互換性）
    "ColoredFormatter",
    "JSONFormatter",
]

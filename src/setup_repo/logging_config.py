"""
ロギング設定管理モジュール

このモジュールは、プロジェクト全体のロギング設定を管理し、
環境に応じた適切なログレベルとフォーマットを提供します。
"""

import os
from pathlib import Path
from typing import Any, Optional

from .logging_handlers import (
    create_ci_handler,
    create_development_handler,
    create_testing_handler,
)
from .quality_logger import LogLevel, QualityLogger, configure_quality_logging


class LoggingConfig:
    """ロギング設定管理クラス"""

    # 環境変数とログレベルのマッピング
    LOG_LEVEL_MAPPING = {
        "DEBUG": LogLevel.DEBUG,
        "INFO": LogLevel.INFO,
        "WARNING": LogLevel.WARNING,
        "ERROR": LogLevel.ERROR,
        "CRITICAL": LogLevel.CRITICAL,
    }

    @classmethod
    def get_log_level_from_env(cls) -> LogLevel:
        """環境変数からログレベルを取得"""
        env_level = os.getenv("LOG_LEVEL", "INFO").upper()
        return cls.LOG_LEVEL_MAPPING.get(env_level, LogLevel.INFO)

    @classmethod
    def is_debug_mode(cls) -> bool:
        """デバッグモードかどうかを判定"""
        return (
            os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
            or os.getenv("LOG_LEVEL", "").upper() == "DEBUG"
            or os.getenv("CI_DEBUG", "").lower() in ("true", "1", "yes")
        )

    @classmethod
    def is_ci_environment(cls) -> bool:
        """CI環境かどうかを判定"""
        return (
            os.getenv("CI", "").lower() in ("true", "1")
            or os.getenv("GITHUB_ACTIONS", "").lower() == "true"
            or os.getenv("CONTINUOUS_INTEGRATION", "").lower() in ("true", "1")
        )

    @classmethod
    def should_use_json_format(cls) -> bool:
        """JSON形式のログを使用するかどうかを判定"""
        return os.getenv("CI_JSON_LOGS", "").lower() in ("true", "1") or os.getenv(
            "JSON_LOGS", ""
        ).lower() in ("true", "1")

    @classmethod
    def get_log_file_path(cls, log_name: str = "quality") -> Optional[Path]:
        """ログファイルパスを取得"""
        # CI環境では通常ファイルログは不要
        if cls.is_ci_environment() and not os.getenv("CI_LOG_FILE"):
            return None

        # ログディレクトリを環境変数から取得、デフォルトはlogs/
        log_dir = os.getenv("LOG_DIR", "logs")
        log_file = f"{log_name}.log"

        return Path(log_dir) / log_file

    @classmethod
    def configure_for_environment(
        cls, logger_name: str = "setup_repo.quality"
    ) -> QualityLogger:
        """環境に応じたロギング設定を行う"""
        log_level = cls.get_log_level_from_env()
        log_file = cls.get_log_file_path()
        enable_console = True  # 常にコンソール出力を有効
        enable_json_format = cls.should_use_json_format()

        # デバッグモードの場合はより詳細なログを出力
        if cls.is_debug_mode():
            log_level = LogLevel.DEBUG

        return configure_quality_logging(
            log_level=log_level,
            log_file=log_file,
            enable_console=enable_console,
            enable_json_format=enable_json_format,
        )

    @classmethod
    def get_debug_context(cls) -> dict[str, Any]:
        """デバッグ用の環境情報を取得"""
        return {
            "log_level": cls.get_log_level_from_env().value,
            "debug_mode": str(cls.is_debug_mode()),
            "ci_environment": str(cls.is_ci_environment()),
            "json_format": str(cls.should_use_json_format()),
            "log_file": (
                str(cls.get_log_file_path()) if cls.get_log_file_path() else "None"
            ),
            "environment_variables": {
                key: str(value)
                for key, value in os.environ.items()
                if key.startswith(("LOG_", "DEBUG", "CI", "GITHUB_"))
            },
        }


def setup_project_logging() -> QualityLogger:
    """プロジェクト全体のロギングを設定"""
    return LoggingConfig.configure_for_environment()


def setup_ci_logging() -> QualityLogger:
    """CI環境専用のロギングを設定"""
    # CI環境では常にINFOレベル以上、JSON形式を使用
    return configure_quality_logging(
        log_level=(
            LogLevel.INFO if not LoggingConfig.is_debug_mode() else LogLevel.DEBUG
        ),
        log_file=None,  # CI環境ではファイルログは使用しない
        enable_console=True,
        enable_json_format=True,
    )


def setup_development_logging() -> QualityLogger:
    """開発環境専用のロギングを設定"""
    # 開発環境では詳細なログとファイル出力を使用
    return configure_quality_logging(
        log_level=LogLevel.DEBUG,
        log_file=Path("logs/development.log"),
        enable_console=True,
        enable_json_format=False,  # 開発環境では読みやすい形式を使用
    )


def setup_testing_logging() -> QualityLogger:
    """テスト環境専用のロギングを設定"""
    # テスト環境では必要最小限のログ出力
    return configure_quality_logging(
        log_level=LogLevel.WARNING,  # テスト中は警告以上のみ
        log_file=None,
        enable_console=False,  # テスト出力を汚さない
        enable_json_format=False,
    )


# 後方互換性のためのエイリアス
__all__ = [
    "LoggingConfig",
    "setup_project_logging",
    "setup_ci_logging",
    "setup_development_logging",
    "setup_testing_logging",
    # ハンドラー（後方互換性）
    "create_ci_handler",
    "create_development_handler",
    "create_testing_handler",
]

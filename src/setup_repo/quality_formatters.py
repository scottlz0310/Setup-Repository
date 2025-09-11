"""
品質チェック専用のフォーマッター機能

このモジュールは、ログメッセージのフォーマット、色付け、
JSON形式変換などのフォーマッター機能を提供します。
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Optional


class ColoredFormatter(logging.Formatter):
    """色付きログフォーマッター"""

    # ANSI色コード
    COLORS = {
        "DEBUG": "\033[36m",  # シアン
        "INFO": "\033[32m",  # 緑
        "WARNING": "\033[33m",  # 黄
        "ERROR": "\033[31m",  # 赤
        "CRITICAL": "\033[35m",  # マゼンタ
        "RESET": "\033[0m",  # リセット
    }

    def __init__(self, fmt=None, datefmt=None, include_platform_info: bool = False):
        super().__init__(fmt, datefmt)
        self.include_platform_info = include_platform_info
        self._platform_info: Optional[str] = None

    def _get_platform_info(self) -> str:
        """プラットフォーム情報を取得（キャッシュ付き）"""
        if self._platform_info is None and self.include_platform_info:
            try:
                from .platform_detector import detect_platform

                platform_info = detect_platform()
                self._platform_info = f"[{platform_info.name}]"
            except ImportError:
                self._platform_info = "[unknown]"
        return self._platform_info or ""

    def format(self, record):
        # 基本フォーマット
        formatted = super().format(record)

        # プラットフォーム情報を追加
        if self.include_platform_info:
            platform_prefix = self._get_platform_info()
            formatted = f"{platform_prefix} {formatted}"

        # 色を追加
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]

        return f"{color}{formatted}{reset}"


class JSONFormatter(logging.Formatter):
    """JSON形式ログフォーマッター"""

    def __init__(self, include_platform_info: bool = True):
        super().__init__()
        self.include_platform_info = include_platform_info
        self._platform_info: Optional[dict[str, str]] = None

    def _get_platform_info(self) -> dict[str, Any]:
        """プラットフォーム情報を取得（キャッシュ付き）"""
        if self._platform_info is None and self.include_platform_info:
            try:
                from .platform_detector import detect_platform

                platform_info = detect_platform()
                self._platform_info = {
                    "name": platform_info.name,
                    "display_name": platform_info.display_name,
                    "shell": platform_info.shell,
                    "python_cmd": platform_info.python_cmd,
                }
            except ImportError:
                self._platform_info = {"error": "platform_detector not available"}
        return self._platform_info or {}

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

        # プラットフォーム情報を追加
        if self.include_platform_info:
            log_entry["platform"] = self._get_platform_info()

        # コンテキスト情報を追加
        if hasattr(record, "context") and record.context:
            log_entry["context"] = record.context

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def format_log_message(
    message: str,
    level: str = "INFO",
    timestamp: Optional[datetime] = None,
    context: Optional[dict[str, Any]] = None,
) -> str:
    """ログメッセージをフォーマット"""
    if timestamp is None:
        timestamp = datetime.now()

    formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"{formatted_time} - {level} - {message}"

    if context:
        context_str = json.dumps(context, ensure_ascii=False)
        formatted_message += f" - コンテキスト: {context_str}"

    return formatted_message


def add_color_codes(text: str, level: str = "INFO") -> str:
    """テキストに色コードを追加"""
    colors = {
        "DEBUG": "\033[36m",  # シアン
        "INFO": "\033[32m",  # 緑
        "WARNING": "\033[33m",  # 黄
        "ERROR": "\033[31m",  # 赤
        "CRITICAL": "\033[35m",  # マゼンタ
    }

    color = colors.get(level.upper(), "")
    reset = "\033[0m"

    return f"{color}{text}{reset}"


def strip_color_codes(text: str) -> str:
    """テキストから色コードを除去"""
    # ANSI色コードのパターン
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def format_metrics_summary(metrics: dict[str, Any]) -> str:
    """メトリクス概要をフォーマット"""
    lines = ["=== 品質メトリクス概要 ==="]

    for key, value in metrics.items():
        if isinstance(value, bool):  # boolを先にチェック（intのサブクラスのため）
            status = "✅" if value else "❌"
            lines.append(f"{key}: {status}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {value}")

    return "\n".join(lines)


def format_quality_check_result(check_type: str, result: dict[str, Any]) -> str:
    """品質チェック結果をフォーマット"""
    if result.get("success", False):
        message = f"品質チェック成功: {check_type}"
        if "metrics" in result:
            message += f" - メトリクス: {result['metrics']}"
        return message
    else:
        errors = result.get("errors", [])
        error_message = "; ".join(errors) if errors else "不明なエラー"
        message = f"品質チェック失敗: {check_type} - {error_message}"
        if "details" in result:
            message += f" - 詳細: {result['details']}"
        return message

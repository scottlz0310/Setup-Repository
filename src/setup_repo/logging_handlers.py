"""
カスタムログハンドラーとハンドラー作成機能

このモジュールは、プロジェクト固有のログハンドラーと
ハンドラー作成のユーティリティ機能を提供します。
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, TextIO

from .quality_formatters import ColoredFormatter, JSONFormatter


class TeeHandler(logging.Handler):
    """複数の出力先に同時にログを出力するハンドラー"""

    def __init__(self, handlers: list[logging.Handler]):
        super().__init__()
        self.handlers = handlers

    def emit(self, record):
        """全てのハンドラーにレコードを送信"""
        for handler in self.handlers:
            handler.emit(record)

    def set_level(self, level):
        """全てのハンドラーのレベルを設定"""
        super().setLevel(level)
        for handler in self.handlers:
            handler.setLevel(level)

    def set_formatter(self, formatter):
        """全てのハンドラーのフォーマッターを設定"""
        super().setFormatter(formatter)
        for handler in self.handlers:
            handler.setFormatter(formatter)


class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """拡張されたローテーティングファイルハンドラー"""

    def __init__(
        self,
        filename: Path,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        encoding: str = "utf-8",
    ):
        # ディレクトリを作成
        filename.parent.mkdir(parents=True, exist_ok=True)

        super().__init__(
            filename=str(filename),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
        )


class ColoredConsoleHandler(logging.StreamHandler):
    """色付きコンソール出力ハンドラー"""

    def __init__(self, stream: Optional[TextIO] = None):
        super().__init__(stream or sys.stdout)
        self.setFormatter(
            ColoredFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )


def create_file_handler(
    log_file: Path,
    enable_json_format: bool = False,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Handler:
    """ファイルハンドラーを作成"""
    handler = RotatingFileHandler(
        filename=log_file,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )

    if enable_json_format:
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    return handler


def create_console_handler(
    enable_json_format: bool = False,
    enable_colors: bool = True,
    stream: Optional[TextIO] = None,
) -> logging.Handler:
    """コンソールハンドラーを作成"""
    handler = logging.StreamHandler(stream or sys.stdout)

    if enable_json_format:
        formatter: logging.Formatter = JSONFormatter()
    elif enable_colors:
        formatter = ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    return handler


def create_tee_handler(
    console_handler: logging.Handler,
    file_handler: logging.Handler,
) -> TeeHandler:
    """コンソールとファイルの両方に出力するTeeハンドラーを作成"""
    return TeeHandler([console_handler, file_handler])


def create_ci_handler(enable_json_format: bool = True) -> logging.Handler:
    """CI環境専用ハンドラーを作成"""
    return create_console_handler(
        enable_json_format=enable_json_format,
        enable_colors=False,  # CI環境では色を無効化
        stream=sys.stdout,
    )


def create_development_handler(log_file: Optional[Path] = None) -> logging.Handler:
    """開発環境専用ハンドラーを作成"""
    console_handler = create_console_handler(
        enable_json_format=False,
        enable_colors=True,
    )

    if log_file:
        file_handler = create_file_handler(
            log_file=log_file,
            enable_json_format=False,
        )
        return create_tee_handler(console_handler, file_handler)
    else:
        return console_handler


def create_testing_handler() -> logging.Handler:
    """テスト環境専用ハンドラーを作成"""
    # テスト環境では出力を最小限に抑制
    handler = logging.NullHandler()
    return handler

"""
品質フォーマッターモジュールのテスト
"""

import json
import logging
from datetime import datetime

from setup_repo.quality_formatters import (
    ColoredFormatter,
    JSONFormatter,
    add_color_codes,
    format_log_message,
    format_metrics_summary,
    format_quality_check_result,
    strip_color_codes,
)


class TestColoredFormatter:
    """ColoredFormatterクラスのテスト"""

    def test_colored_formatter_creation(self):
        """ColoredFormatterの作成をテスト"""
        formatter = ColoredFormatter()
        assert formatter is not None

    def test_colored_formatter_format(self):
        """色付きフォーマットのテスト"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        
        # ログレコードを作成
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="テストメッセージ",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # 色コードが含まれていることを確認
        assert "\033[32m" in formatted  # 緑色（INFO）
        assert "\033[0m" in formatted   # リセット
        assert "テストメッセージ" in formatted

    def test_different_log_levels_colors(self):
        """異なるログレベルの色付けをテスト"""
        formatter = ColoredFormatter("%(levelname)s - %(message)s")
        
        levels_and_colors = [
            (logging.DEBUG, "\033[36m"),    # シアン
            (logging.INFO, "\033[32m"),     # 緑
            (logging.WARNING, "\033[33m"),  # 黄
            (logging.ERROR, "\033[31m"),    # 赤
            (logging.CRITICAL, "\033[35m"), # マゼンタ
        ]
        
        for level, expected_color in levels_and_colors:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="",
                lineno=0,
                msg="テストメッセージ",
                args=(),
                exc_info=None
            )
            
            formatted = formatter.format(record)
            assert expected_color in formatted


class TestJSONFormatter:
    """JSONFormatterクラスのテスト"""

    def test_json_formatter_creation(self):
        """JSONFormatterの作成をテスト"""
        formatter = JSONFormatter()
        assert formatter is not None

    def test_json_formatter_format(self):
        """JSON形式フォーマットのテスト"""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="テストメッセージ",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        
        # JSON形式であることを確認
        log_entry = json.loads(formatted)
        
        assert log_entry["level"] == "INFO"
        assert log_entry["logger"] == "test_logger"
        assert log_entry["message"] == "テストメッセージ"
        assert log_entry["module"] == "test_module"
        assert log_entry["function"] == "test_function"
        assert log_entry["line"] == 42
        assert "timestamp" in log_entry

    def test_json_formatter_with_exception(self):
        """例外情報付きJSON形式フォーマットのテスト"""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("テスト例外")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="エラーメッセージ",
                args=(),
                exc_info=exc_info
            )
            
            formatted = formatter.format(record)
            log_entry = json.loads(formatted)
            
            assert "exception" in log_entry
            assert "ValueError" in log_entry["exception"]


class TestFormatFunctions:
    """フォーマット関数のテスト"""

    def test_format_log_message(self):
        """ログメッセージフォーマットのテスト"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        
        # 基本的なフォーマット
        formatted = format_log_message("テストメッセージ", "INFO", timestamp)
        assert "2024-01-01 12:00:00" in formatted
        assert "INFO" in formatted
        assert "テストメッセージ" in formatted
        
        # コンテキスト付きフォーマット
        context = {"key": "value", "number": 42}
        formatted_with_context = format_log_message(
            "コンテキストメッセージ", "ERROR", timestamp, context
        )
        assert "コンテキスト" in formatted_with_context
        assert "key" in formatted_with_context
        assert "value" in formatted_with_context

    def test_add_color_codes(self):
        """色コード追加のテスト"""
        text = "テストテキスト"
        
        # 各レベルの色コードテスト
        levels_and_colors = [
            ("DEBUG", "\033[36m"),    # シアン
            ("INFO", "\033[32m"),     # 緑
            ("WARNING", "\033[33m"),  # 黄
            ("ERROR", "\033[31m"),    # 赤
            ("CRITICAL", "\033[35m"), # マゼンタ
        ]
        
        for level, expected_color in levels_and_colors:
            colored = add_color_codes(text, level)
            assert colored.startswith(expected_color)
            assert colored.endswith("\033[0m")  # リセット
            assert text in colored
        
        # 不明なレベルの場合
        unknown_colored = add_color_codes(text, "UNKNOWN")
        assert unknown_colored == f"{text}\033[0m"

    def test_strip_color_codes(self):
        """色コード除去のテスト"""
        # 色付きテキスト
        colored_text = "\033[32mテストテキスト\033[0m"
        stripped = strip_color_codes(colored_text)
        assert stripped == "テストテキスト"
        
        # 複数の色コードを含むテキスト
        multi_colored = "\033[31mエラー:\033[0m \033[33m警告メッセージ\033[0m"
        stripped_multi = strip_color_codes(multi_colored)
        assert stripped_multi == "エラー: 警告メッセージ"
        
        # 色コードがないテキスト
        plain_text = "普通のテキスト"
        stripped_plain = strip_color_codes(plain_text)
        assert stripped_plain == plain_text

    def test_format_metrics_summary(self):
        """メトリクス概要フォーマットのテスト"""
        metrics = {
            "score": 85.5,
            "errors": 2,
            "passed": True,
            "failed": False,
            "name": "テストメトリクス"
        }
        
        formatted = format_metrics_summary(metrics)
        
        assert "=== 品質メトリクス概要 ===" in formatted
        assert "score: 85.5" in formatted
        assert "errors: 2" in formatted
        assert "passed: ✅" in formatted
        assert "failed: ❌" in formatted
        assert "name: テストメトリクス" in formatted

    def test_format_quality_check_result_success(self):
        """品質チェック結果フォーマット（成功）のテスト"""
        result = {
            "success": True,
            "metrics": {"coverage": 85.0, "issues": 0}
        }
        
        formatted = format_quality_check_result("TestCheck", result)
        
        assert "品質チェック成功: TestCheck" in formatted
        assert "メトリクス" in formatted
        assert "coverage" in formatted

    def test_format_quality_check_result_failure(self):
        """品質チェック結果フォーマット（失敗）のテスト"""
        result = {
            "success": False,
            "errors": ["エラー1", "エラー2"],
            "details": {"stage": "lint", "tool": "ruff"}
        }
        
        formatted = format_quality_check_result("TestCheck", result)
        
        assert "品質チェック失敗: TestCheck" in formatted
        assert "エラー1; エラー2" in formatted
        assert "詳細" in formatted
        assert "stage" in formatted

    def test_format_quality_check_result_no_errors(self):
        """品質チェック結果フォーマット（エラー情報なし）のテスト"""
        result = {"success": False}
        
        formatted = format_quality_check_result("TestCheck", result)
        
        assert "品質チェック失敗: TestCheck" in formatted
        assert "不明なエラー" in formatted
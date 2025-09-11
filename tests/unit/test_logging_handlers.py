"""
ログハンドラーモジュールのテスト
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from setup_repo.logging_handlers import (
    ColoredConsoleHandler,
    RotatingFileHandler,
    TeeHandler,
    create_ci_handler,
    create_console_handler,
    create_development_handler,
    create_file_handler,
    create_tee_handler,
    create_testing_handler,
)


class TestTeeHandler:
    """TeeHandlerクラスのテスト"""

    def test_tee_handler_creation(self):
        """TeeHandlerの作成をテスト"""
        handler1 = MagicMock(spec=logging.Handler)
        handler2 = MagicMock(spec=logging.Handler)

        tee_handler = TeeHandler([handler1, handler2])

        assert len(tee_handler.handlers) == 2
        assert handler1 in tee_handler.handlers
        assert handler2 in tee_handler.handlers

    def test_tee_handler_emit(self):
        """TeeHandlerのemitメソッドをテスト"""
        handler1 = MagicMock(spec=logging.Handler)
        handler2 = MagicMock(spec=logging.Handler)

        tee_handler = TeeHandler([handler1, handler2])

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="テストメッセージ",
            args=(),
            exc_info=None,
        )

        tee_handler.emit(record)

        handler1.emit.assert_called_once_with(record)
        handler2.emit.assert_called_once_with(record)

    def test_tee_handler_set_level(self):
        """TeeHandlerのset_levelメソッドをテスト"""
        handler1 = MagicMock(spec=logging.Handler)
        handler2 = MagicMock(spec=logging.Handler)

        tee_handler = TeeHandler([handler1, handler2])
        tee_handler.set_level(logging.DEBUG)

        handler1.setLevel.assert_called_once_with(logging.DEBUG)
        handler2.setLevel.assert_called_once_with(logging.DEBUG)

    def test_tee_handler_set_formatter(self):
        """TeeHandlerのset_formatterメソッドをテスト"""
        handler1 = MagicMock(spec=logging.Handler)
        handler2 = MagicMock(spec=logging.Handler)
        formatter = MagicMock(spec=logging.Formatter)

        tee_handler = TeeHandler([handler1, handler2])
        tee_handler.set_formatter(formatter)

        handler1.setFormatter.assert_called_once_with(formatter)
        handler2.setFormatter.assert_called_once_with(formatter)


class TestRotatingFileHandler:
    """RotatingFileHandlerクラスのテスト"""

    def test_rotating_file_handler_creation(self):
        """RotatingFileHandlerの作成をテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            handler = RotatingFileHandler(
                filename=log_file,
                max_bytes=1024,
                backup_count=3,
            )

            assert handler.maxBytes == 1024
            assert handler.backupCount == 3
            assert log_file.parent.exists()

    def test_rotating_file_handler_directory_creation(self):
        """RotatingFileHandlerのディレクトリ作成をテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "subdir" / "test.log"

            # サブディレクトリは存在しない
            assert not log_file.parent.exists()

            RotatingFileHandler(filename=log_file)

            # ハンドラー作成時にディレクトリが作成される
            assert log_file.parent.exists()


class TestColoredConsoleHandler:
    """ColoredConsoleHandlerクラスのテスト"""

    def test_colored_console_handler_creation(self):
        """ColoredConsoleHandlerの作成をテスト"""
        handler = ColoredConsoleHandler()

        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None

    def test_colored_console_handler_with_stream(self):
        """ストリーム指定でのColoredConsoleHandlerの作成をテスト"""
        import io

        stream = io.StringIO()

        handler = ColoredConsoleHandler(stream)

        assert handler.stream is stream


class TestHandlerCreationFunctions:
    """ハンドラー作成関数のテスト"""

    def test_create_file_handler(self):
        """create_file_handlerのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            handler = create_file_handler(log_file)

            assert isinstance(handler, RotatingFileHandler)
            assert handler.formatter is not None

    def test_create_file_handler_with_json(self):
        """JSON形式でのcreate_file_handlerのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            handler = create_file_handler(log_file, enable_json_format=True)

            assert isinstance(handler, RotatingFileHandler)
            # JSONFormatterが設定されていることを確認
            assert handler.formatter is not None

    def test_create_console_handler(self):
        """create_console_handlerのテスト"""
        handler = create_console_handler()

        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None

    def test_create_console_handler_json(self):
        """JSON形式でのcreate_console_handlerのテスト"""
        handler = create_console_handler(enable_json_format=True)

        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None

    def test_create_console_handler_no_colors(self):
        """色なしでのcreate_console_handlerのテスト"""
        handler = create_console_handler(enable_colors=False)

        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None

    def test_create_tee_handler(self):
        """create_tee_handlerのテスト"""
        console_handler = create_console_handler()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            file_handler = create_file_handler(log_file)

            tee_handler = create_tee_handler(console_handler, file_handler)

            assert isinstance(tee_handler, TeeHandler)
            assert len(tee_handler.handlers) == 2

    def test_create_ci_handler(self):
        """create_ci_handlerのテスト"""
        handler = create_ci_handler()

        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None

    def test_create_ci_handler_no_json(self):
        """JSON無しでのcreate_ci_handlerのテスト"""
        handler = create_ci_handler(enable_json_format=False)

        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None

    def test_create_development_handler_console_only(self):
        """コンソールのみでのcreate_development_handlerのテスト"""
        handler = create_development_handler()

        assert isinstance(handler, logging.StreamHandler)

    def test_create_development_handler_with_file(self):
        """ファイル付きでのcreate_development_handlerのテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "dev.log"

            handler = create_development_handler(log_file)

            assert isinstance(handler, TeeHandler)
            assert len(handler.handlers) == 2

    def test_create_testing_handler(self):
        """create_testing_handlerのテスト"""
        handler = create_testing_handler()

        assert isinstance(handler, logging.NullHandler)

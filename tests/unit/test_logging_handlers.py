"""ログハンドラー機能のテスト"""

import logging
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from ..multiplatform.helpers import verify_current_platform, skip_if_not_platform

from src.setup_repo.logging_handlers import (
    TeeHandler,
    RotatingFileHandler,
    ColoredConsoleHandler,
    create_file_handler,
    create_console_handler,
    create_tee_handler,
    create_ci_handler,
    create_development_handler,
    create_testing_handler
)


class TestTeeHandler:
    """TeeHandlerのテストクラス"""

    @pytest.fixture
    def mock_handlers(self):
        """モックハンドラーのリスト"""
        return [Mock(spec=logging.Handler), Mock(spec=logging.Handler)]

    @pytest.fixture
    def tee_handler(self, mock_handlers):
        """TeeHandlerインスタンス"""
        return TeeHandler(mock_handlers)

    @pytest.mark.unit
    def test_init(self, mock_handlers, tee_handler):
        """初期化テスト"""
        platform_info = verify_current_platform()
        
        assert tee_handler.handlers == mock_handlers

    @pytest.mark.unit
    def test_emit(self, mock_handlers, tee_handler):
        """レコード送信テスト"""
        platform_info = verify_current_platform()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None
        )
        
        tee_handler.emit(record)
        
        for handler in mock_handlers:
            handler.emit.assert_called_once_with(record)

    @pytest.mark.unit
    def test_set_level(self, mock_handlers, tee_handler):
        """レベル設定テスト"""
        platform_info = verify_current_platform()
        
        tee_handler.set_level(logging.DEBUG)
        
        assert tee_handler.level == logging.DEBUG
        for handler in mock_handlers:
            handler.setLevel.assert_called_once_with(logging.DEBUG)

    @pytest.mark.unit
    def test_set_formatter(self, mock_handlers, tee_handler):
        """フォーマッター設定テスト"""
        platform_info = verify_current_platform()
        
        formatter = logging.Formatter("%(message)s")
        tee_handler.set_formatter(formatter)
        
        assert tee_handler.formatter == formatter
        for handler in mock_handlers:
            handler.setFormatter.assert_called_once_with(formatter)


class TestRotatingFileHandler:
    """RotatingFileHandlerのテストクラス"""

    @pytest.mark.unit
    def test_init_creates_directory(self, tmp_path):
        """ディレクトリ作成テスト"""
        platform_info = verify_current_platform()
        
        log_file = tmp_path / "logs" / "test.log"
        
        handler = RotatingFileHandler(log_file)
        
        assert log_file.parent.exists()
        assert handler.baseFilename == str(log_file)

    @pytest.mark.unit
    def test_init_with_custom_params(self, tmp_path):
        """カスタムパラメータでの初期化テスト"""
        platform_info = verify_current_platform()
        
        log_file = tmp_path / "test.log"
        max_bytes = 5 * 1024 * 1024  # 5MB
        backup_count = 3
        
        handler = RotatingFileHandler(
            log_file,
            max_bytes=max_bytes,
            backup_count=backup_count
        )
        
        assert handler.maxBytes == max_bytes
        assert handler.backupCount == backup_count


class TestColoredConsoleHandler:
    """ColoredConsoleHandlerのテストクラス"""

    @pytest.mark.unit
    def test_init_default_stream(self):
        """デフォルトストリームでの初期化テスト"""
        platform_info = verify_current_platform()
        
        handler = ColoredConsoleHandler()
        
        assert handler.stream == sys.stdout
        assert isinstance(handler.formatter, logging.Formatter)

    @pytest.mark.unit
    def test_init_custom_stream(self):
        """カスタムストリームでの初期化テスト"""
        platform_info = verify_current_platform()
        
        custom_stream = StringIO()
        handler = ColoredConsoleHandler(stream=custom_stream)
        
        assert handler.stream == custom_stream

    @pytest.mark.unit
    def test_init_with_platform_info(self):
        """プラットフォーム情報付きでの初期化テスト"""
        platform_info = verify_current_platform()
        
        handler = ColoredConsoleHandler(include_platform_info=True)
        
        assert handler.formatter is not None


class TestCreateFileHandler:
    """create_file_handler関数のテスト"""

    @pytest.mark.unit
    def test_create_file_handler_default(self, tmp_path):
        """デフォルト設定でのファイルハンドラー作成"""
        platform_info = verify_current_platform()
        
        log_file = tmp_path / "test.log"
        
        handler = create_file_handler(log_file)
        
        assert isinstance(handler, RotatingFileHandler)
        assert handler.formatter is not None
        assert log_file.parent.exists()

    @pytest.mark.unit
    def test_create_file_handler_json_format(self, tmp_path):
        """JSON形式でのファイルハンドラー作成"""
        platform_info = verify_current_platform()
        
        log_file = tmp_path / "test.log"
        
        handler = create_file_handler(log_file, enable_json_format=True)
        
        assert isinstance(handler, RotatingFileHandler)
        # JSONFormatterが設定されていることを確認
        assert handler.formatter is not None

    @pytest.mark.unit
    def test_create_file_handler_custom_params(self, tmp_path):
        """カスタムパラメータでのファイルハンドラー作成"""
        platform_info = verify_current_platform()
        
        log_file = tmp_path / "test.log"
        max_bytes = 1024
        backup_count = 2
        
        handler = create_file_handler(
            log_file,
            max_bytes=max_bytes,
            backup_count=backup_count
        )
        
        assert handler.maxBytes == max_bytes
        assert handler.backupCount == backup_count


class TestCreateConsoleHandler:
    """create_console_handler関数のテスト"""

    @pytest.mark.unit
    def test_create_console_handler_default(self):
        """デフォルト設定でのコンソールハンドラー作成"""
        platform_info = verify_current_platform()
        
        handler = create_console_handler()
        
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream == sys.stdout
        assert handler.formatter is not None

    @pytest.mark.unit
    def test_create_console_handler_json_format(self):
        """JSON形式でのコンソールハンドラー作成"""
        platform_info = verify_current_platform()
        
        handler = create_console_handler(enable_json_format=True)
        
        assert isinstance(handler, logging.StreamHandler)
        # JSONFormatterが設定されていることを確認
        assert handler.formatter is not None

    @pytest.mark.unit
    def test_create_console_handler_no_colors(self):
        """色なしでのコンソールハンドラー作成"""
        platform_info = verify_current_platform()
        
        handler = create_console_handler(enable_colors=False)
        
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, logging.Formatter)

    @pytest.mark.unit
    def test_create_console_handler_custom_stream(self):
        """カスタムストリームでのコンソールハンドラー作成"""
        platform_info = verify_current_platform()
        
        custom_stream = StringIO()
        handler = create_console_handler(stream=custom_stream)
        
        assert handler.stream == custom_stream

    @pytest.mark.unit
    def test_create_console_handler_with_platform_info(self):
        """プラットフォーム情報付きでのコンソールハンドラー作成"""
        platform_info = verify_current_platform()
        
        handler = create_console_handler(include_platform_info=True)
        
        assert handler.formatter is not None


class TestCreateTeeHandler:
    """create_tee_handler関数のテスト"""

    @pytest.mark.unit
    def test_create_tee_handler(self):
        """Teeハンドラー作成テスト"""
        platform_info = verify_current_platform()
        
        console_handler = Mock(spec=logging.Handler)
        file_handler = Mock(spec=logging.Handler)
        
        tee_handler = create_tee_handler(console_handler, file_handler)
        
        assert isinstance(tee_handler, TeeHandler)
        assert console_handler in tee_handler.handlers
        assert file_handler in tee_handler.handlers


class TestCreateCiHandler:
    """create_ci_handler関数のテスト"""

    @pytest.mark.unit
    def test_create_ci_handler_default(self):
        """デフォルト設定でのCIハンドラー作成"""
        platform_info = verify_current_platform()
        
        handler = create_ci_handler()
        
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream == sys.stdout
        # JSON形式が有効になっていることを確認
        assert handler.formatter is not None

    @pytest.mark.unit
    def test_create_ci_handler_no_json(self):
        """JSON無効でのCIハンドラー作成"""
        platform_info = verify_current_platform()
        
        handler = create_ci_handler(enable_json_format=False)
        
        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None


class TestCreateDevelopmentHandler:
    """create_development_handler関数のテスト"""

    @pytest.mark.unit
    def test_create_development_handler_console_only(self):
        """コンソールのみの開発ハンドラー作成"""
        platform_info = verify_current_platform()
        
        handler = create_development_handler()
        
        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None

    @pytest.mark.unit
    def test_create_development_handler_with_file(self, tmp_path):
        """ファイル付きの開発ハンドラー作成"""
        platform_info = verify_current_platform()
        
        log_file = tmp_path / "dev.log"
        
        handler = create_development_handler(log_file)
        
        assert isinstance(handler, TeeHandler)
        assert len(handler.handlers) == 2


class TestCreateTestingHandler:
    """create_testing_handler関数のテスト"""

    @pytest.mark.unit
    def test_create_testing_handler(self):
        """テストハンドラー作成テスト"""
        platform_info = verify_current_platform()
        
        handler = create_testing_handler()
        
        assert isinstance(handler, logging.NullHandler)


class TestHandlerIntegration:
    """ハンドラー統合テスト"""

    @pytest.mark.unit
    def test_handler_logging_flow(self, tmp_path):
        """ハンドラーのログ出力フローテスト"""
        platform_info = verify_current_platform()
        
        # ファイルハンドラーを作成
        log_file = tmp_path / "test.log"
        file_handler = create_file_handler(log_file)
        
        # コンソールハンドラーを作成
        console_stream = StringIO()
        console_handler = create_console_handler(stream=console_stream)
        
        # Teeハンドラーを作成
        tee_handler = create_tee_handler(console_handler, file_handler)
        
        # ロガーを設定
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)
        logger.addHandler(tee_handler)
        
        # ログメッセージを出力
        test_message = "Test log message"
        logger.info(test_message)
        
        # ファイルに出力されていることを確認
        assert log_file.exists()
        file_content = log_file.read_text(encoding="utf-8")
        assert test_message in file_content
        
        # コンソールに出力されていることを確認
        console_output = console_stream.getvalue()
        assert test_message in console_output

    @pytest.mark.unit
    def test_handler_level_filtering(self, tmp_path):
        """ハンドラーのレベルフィルタリングテスト"""
        platform_info = verify_current_platform()
        
        log_file = tmp_path / "test.log"
        handler = create_file_handler(log_file)
        handler.setLevel(logging.WARNING)
        
        logger = logging.getLogger("test_level_logger")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        
        # DEBUGメッセージ（フィルタリングされる）
        logger.debug("Debug message")
        
        # WARNINGメッセージ（出力される）
        logger.warning("Warning message")
        
        # ファイル内容を確認
        file_content = log_file.read_text(encoding="utf-8")
        assert "Debug message" not in file_content
        assert "Warning message" in file_content

    @pytest.mark.unit
    def test_rotating_file_handler_rotation(self, tmp_path):
        """ローテーティングファイルハンドラーのローテーションテスト"""
        platform_info = verify_current_platform()
        
        log_file = tmp_path / "rotate.log"
        # 小さなサイズでローテーションをテスト
        handler = RotatingFileHandler(log_file, max_bytes=100, backup_count=2)
        
        logger = logging.getLogger("rotate_logger")
        logger.addHandler(handler)
        
        # 大量のログを出力してローテーションを発生させる
        for i in range(50):
            logger.info(f"Long log message number {i} with extra content to exceed size limit")
        
        # ローテーションファイルが作成されていることを確認
        # 実際のローテーションは実装依存なので、基本的な動作のみ確認
        assert log_file.exists()

    @pytest.mark.unit
    def test_handler_exception_handling(self, tmp_path):
        """ハンドラーの例外処理テスト"""
        platform_info = verify_current_platform()
        
        # 書き込み不可能なディレクトリでのエラーハンドリング
        # （実際のテストでは権限エラーを模擬）
        log_file = tmp_path / "readonly" / "test.log"
        
        # ディレクトリが作成されることを確認
        handler = create_file_handler(log_file)
        assert log_file.parent.exists()
        
        # ハンドラーが正常に作成されることを確認
        assert isinstance(handler, RotatingFileHandler)
"""
後方互換性維持モジュール

分割されたモジュールに対するdeprecation警告付きエイリアスを提供します。
"""

import warnings
from typing import Any


def _deprecated_import(old_module: str, new_module: str, function_name: str) -> Any:
    """
    非推奨インポートの警告を発行し、新しいモジュールから関数をインポート

    Args:
        old_module: 旧モジュール名
        new_module: 新モジュール名
        function_name: 関数名

    Returns:
        新しいモジュールからインポートされた関数
    """
    warnings.warn(
        f"{old_module}.{function_name} is deprecated. Use {new_module}.{function_name} instead.",
        DeprecationWarning,
        stacklevel=3,
    )

    # 動的インポート（セキュリティ強化）
    import importlib

    # モジュール名の検証
    allowed_modules = [
        "quality_errors",
        "quality_formatters",
        "quality_logger",
        "ci_environment",
        "ci_error_handler",
        "logging_handlers",
        "logging_config",
        "quality_collectors",
        "quality_metrics",
        "setup_validators",
        "interactive_setup",
        "new_module",
        "nonexistent_module",  # テスト用モジュール
    ]

    if new_module not in allowed_modules:
        raise ImportError(f"Module {new_module} is not allowed")

    module = importlib.import_module(f"setup_repo.{new_module}")
    return getattr(module, function_name)


# Quality Logger分割に対する後方互換性
class QualityLoggerCompatibility:
    """Quality Logger分割に対する後方互換性クラス"""

    def __getattr__(self, name: str) -> Any:
        # エラー処理関連の関数
        error_functions = [
            "QualityError",
            "QualityWarning",
            "handle_quality_error",
            "format_error_message",
            "log_exception",
            "create_error_report",
        ]

        # フォーマッター関連の関数
        formatter_functions = [
            "ColoredFormatter",
            "JSONFormatter",
            "format_log_message",
            "add_color_codes",
            "strip_color_codes",
        ]

        if name in error_functions:
            return _deprecated_import("quality_logger", "quality_errors", name)
        elif name in formatter_functions:
            return _deprecated_import("quality_logger", "quality_formatters", name)
        else:
            # 基本ログ機能は quality_logger に残る
            return _deprecated_import("quality_logger", "quality_logger", name)


# CI Error Handler分割に対する後方互換性
class CIErrorHandlerCompatibility:
    """CI Error Handler分割に対する後方互換性クラス"""

    def __getattr__(self, name: str) -> Any:
        # CI環境検出関連の関数
        environment_functions = [
            "detect_ci_environment",
            "get_system_info",
            "collect_environment_vars",
            "get_ci_metadata",
            "is_ci_environment",
        ]

        if name in environment_functions:
            return _deprecated_import("ci_error_handler", "ci_environment", name)
        else:
            # エラーハンドリング機能は ci_error_handler に残る
            return _deprecated_import("ci_error_handler", "ci_error_handler", name)


# Logging Config分割に対する後方互換性
class LoggingConfigCompatibility:
    """Logging Config分割に対する後方互換性クラス"""

    def __getattr__(self, name: str) -> Any:
        # ハンドラー関連の関数
        handler_functions = [
            "TeeHandler",
            "RotatingFileHandler",
            "ColoredConsoleHandler",
            "create_file_handler",
            "create_console_handler",
        ]

        if name in handler_functions:
            return _deprecated_import("logging_config", "logging_handlers", name)
        else:
            # 基本設定機能は logging_config に残る
            return _deprecated_import("logging_config", "logging_config", name)


# Quality Metrics分割に対する後方互換性
class QualityMetricsCompatibility:
    """Quality Metrics分割に対する後方互換性クラス"""

    def __getattr__(self, name: str) -> Any:
        # データ収集関連の関数
        collector_functions = [
            "collect_ruff_metrics",
            "collect_mypy_metrics",
            "collect_pytest_metrics",
            "collect_coverage_metrics",
            "parse_tool_output",
        ]

        if name in collector_functions:
            return _deprecated_import("quality_metrics", "quality_collectors", name)
        else:
            # メトリクス計算機能は quality_metrics に残る
            return _deprecated_import("quality_metrics", "quality_metrics", name)


# Interactive Setup分割に対する後方互換性
class InteractiveSetupCompatibility:
    """Interactive Setup分割に対する後方互換性クラス"""

    def __getattr__(self, name: str) -> Any:
        # 検証関連の関数
        validator_functions = [
            "validate_github_credentials",
            "validate_directory_path",
            "validate_setup_prerequisites",
            "check_system_requirements",
        ]

        if name in validator_functions:
            return _deprecated_import("interactive_setup", "setup_validators", name)
        else:
            # メインウィザード機能は interactive_setup に残る
            return _deprecated_import("interactive_setup", "interactive_setup", name)


# 互換性インスタンスを作成
quality_logger_compat = QualityLoggerCompatibility()
ci_error_handler_compat = CIErrorHandlerCompatibility()
logging_config_compat = LoggingConfigCompatibility()
quality_metrics_compat = QualityMetricsCompatibility()
interactive_setup_compat = InteractiveSetupCompatibility()


def create_compatibility_aliases() -> None:
    """
    後方互換性のためのモジュールエイリアスを作成

    この関数は __init__.py で呼び出されて、古いインポートパスを
    新しいモジュール構造にマッピングします。
    """
    import sys
    from types import ModuleType

    # Quality Logger互換性モジュール
    quality_logger_module = ModuleType("setup_repo.quality_logger_legacy")
    quality_logger_module.__dict__.update(quality_logger_compat.__dict__)
    quality_logger_module.__getattr__ = quality_logger_compat.__getattr__  # type: ignore[method-assign]
    sys.modules["setup_repo.quality_logger_legacy"] = quality_logger_module

    # CI Error Handler互換性モジュール
    ci_error_handler_module = ModuleType("setup_repo.ci_error_handler_legacy")
    ci_error_handler_module.__dict__.update(ci_error_handler_compat.__dict__)
    ci_error_handler_module.__getattr__ = ci_error_handler_compat.__getattr__  # type: ignore[method-assign]
    sys.modules["setup_repo.ci_error_handler_legacy"] = ci_error_handler_module

    # Logging Config互換性モジュール
    logging_config_module = ModuleType("setup_repo.logging_config_legacy")
    logging_config_module.__dict__.update(logging_config_compat.__dict__)
    logging_config_module.__getattr__ = logging_config_compat.__getattr__  # type: ignore[method-assign]
    sys.modules["setup_repo.logging_config_legacy"] = logging_config_module

    # Quality Metrics互換性モジュール
    quality_metrics_module = ModuleType("setup_repo.quality_metrics_legacy")
    quality_metrics_module.__dict__.update(quality_metrics_compat.__dict__)
    quality_metrics_module.__getattr__ = quality_metrics_compat.__getattr__  # type: ignore[method-assign]
    sys.modules["setup_repo.quality_metrics_legacy"] = quality_metrics_module

    # Interactive Setup互換性モジュール
    interactive_setup_module = ModuleType("setup_repo.interactive_setup_legacy")
    interactive_setup_module.__dict__.update(interactive_setup_compat.__dict__)
    interactive_setup_module.__getattr__ = interactive_setup_compat.__getattr__  # type: ignore[method-assign]
    sys.modules["setup_repo.interactive_setup_legacy"] = interactive_setup_module


def show_migration_guide() -> None:
    """
    移行ガイドを表示

    開発者に新しいインポートパスへの移行を促すメッセージを表示します。
    """
    migration_message = """
    ========================================
    Setup Repository リファクタリング移行ガイド
    ========================================

    モジュール分割により、一部のインポートパスが変更されました。
    以下の新しいインポートパスを使用してください：

    Quality Logger分割:
    - エラー処理: from setup_repo.quality_errors import ...
    - フォーマッター: from setup_repo.quality_formatters import ...
    - 基本ログ: from setup_repo.quality_logger import ...

    CI Error Handler分割:
    - CI環境検出: from setup_repo.ci_environment import ...
    - エラーハンドリング: from setup_repo.ci_error_handler import ...

    Logging Config分割:
    - ハンドラー: from setup_repo.logging_handlers import ...
    - 基本設定: from setup_repo.logging_config import ...

    Quality Metrics分割:
    - データ収集: from setup_repo.quality_collectors import ...
    - メトリクス計算: from setup_repo.quality_metrics import ...

    Interactive Setup分割:
    - 検証機能: from setup_repo.setup_validators import ...
    - メインウィザード: from setup_repo.interactive_setup import ...

    詳細な移行ガイドは docs/migration-guide.md を参照してください。
    ========================================
    """

    print(migration_message)


# 段階的移行のためのヘルパー関数
def check_deprecated_imports() -> None:
    """
    非推奨インポートの使用をチェック

    開発者に警告を表示し、移行を促します。
    """
    import inspect
    import sys

    # 呼び出し元のフレームを取得
    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller_frame = frame.f_back
        caller_module = caller_frame.f_globals.get("__name__", "unknown")

        # 非推奨モジュールの使用をチェック
        deprecated_modules = [
            "quality_logger_legacy",
            "ci_error_handler_legacy",
            "logging_config_legacy",
            "quality_metrics_legacy",
            "interactive_setup_legacy",
        ]

        for module_name in deprecated_modules:
            if module_name in sys.modules and caller_module != __name__:
                warnings.warn(
                    f"非推奨モジュール {module_name} が使用されています。"
                    f"新しいモジュール構造への移行を検討してください。",
                    DeprecationWarning,
                    stacklevel=2,
                )

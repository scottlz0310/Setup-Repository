"""
ロギング設定管理モジュール

このモジュールは、プロジェクト全体のロギング設定を管理し、
環境に応じた適切なログレベルとフォーマットを提供します。
"""

import os
import platform
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
        return os.getenv("CI_JSON_LOGS", "").lower() in ("true", "1") or os.getenv("JSON_LOGS", "").lower() in (
            "true",
            "1",
        )

    @classmethod
    def get_log_file_path(cls, log_name: str = "quality") -> Optional[Path]:
        """ログファイルパスを取得（クロスプラットフォーム対応）"""
        # CI環境では通常ファイルログは不要（明示的に指定された場合を除く）
        if cls.is_ci_environment() and not os.getenv("CI_LOG_FILE") and not os.getenv("LOG_DIR"):
            return None

        # ログディレクトリを環境変数から取得、デフォルトはlogs/
        log_dir = os.getenv("LOG_DIR", "logs")
        log_file = f"{log_name}.log"

        # クロスプラットフォーム対応: Pathクラスを直接使用
        try:
            # Pathクラスを使用してプラットフォーム固有のパス区切り文字を自動処理
            return Path(log_dir) / log_file
        except (OSError, NotImplementedError) as e:
            # パス作成に失敗した場合は、現在のディレクトリを基準にする
            import logging

            logging.warning(f"ログパス作成に失敗、デフォルトパスを使用: {e}")
            try:
                return Path.cwd() / "logs" / log_file
            except Exception:
                # 最後の手段として現在のプラットフォーム用のPathを直接作成
                if platform.system() == "Windows":
                    from pathlib import WindowsPath

                    return WindowsPath("logs") / log_file
                else:
                    from pathlib import PosixPath

                    return PosixPath("logs") / log_file

    @classmethod
    def configure_for_environment(cls, logger_name: str = "setup_repo.quality") -> QualityLogger:
        """環境に応じたロギング設定を行う"""
        log_level = cls.get_log_level_from_env()
        log_file = cls.get_log_file_path()
        enable_console = True  # 常にコンソール出力を有効
        enable_json_format = cls.should_use_json_format()

        # デバッグモードの場合はより詳細なログを出力
        if cls.is_debug_mode():
            log_level = LogLevel.DEBUG

        logger = configure_quality_logging(
            log_level=log_level,
            log_file=log_file,
            enable_console=enable_console,
            enable_json_format=enable_json_format,
        )

        # プラットフォーム情報をログに記録
        if cls.is_debug_mode():
            debug_context = cls.get_debug_context()
            logger.debug("ロギング設定完了", extra={"context": debug_context})

        return logger

    @classmethod
    def get_debug_context(cls) -> dict[str, Any]:
        """デバッグ用の環境情報を取得"""
        from .platform_detector import PlatformDetector

        detector = PlatformDetector()
        platform_info = detector.get_platform_info()

        context = {
            "log_level": cls.get_log_level_from_env().value,
            "debug_mode": str(cls.is_debug_mode()),
            "ci_environment": str(cls.is_ci_environment()),
            "json_format": str(cls.should_use_json_format()),
            "log_file": (str(cls.get_log_file_path()) if cls.get_log_file_path() else "None"),
            "platform_info": {
                "name": platform_info.name,
                "display_name": platform_info.display_name,
                "shell": platform_info.shell,
                "python_cmd": platform_info.python_cmd,
                "package_managers": platform_info.package_managers,
            },
            "system_info": {
                "platform_system": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "platform_machine": platform.machine(),
                "platform_processor": platform.processor(),
            },
            "environment_variables": {
                key: str(value)
                for key, value in os.environ.items()
                if key.startswith(("LOG_", "DEBUG", "CI", "GITHUB_", "RUNNER_"))
            },
        }

        # CI環境の場合は追加の診断情報を含める
        if cls.is_ci_environment():
            context["ci_diagnostics"] = detector.diagnose_issues()
            context["ci_info"] = detector.get_ci_info()

        return context


def setup_project_logging() -> QualityLogger:
    """プロジェクト全体のロギングを設定"""
    return LoggingConfig.configure_for_environment()


def setup_ci_logging() -> QualityLogger:
    """CI環境専用のロギングを設定"""
    # CI環境では常にINFOレベル以上、JSON形式を使用
    return configure_quality_logging(
        log_level=(LogLevel.INFO if not LoggingConfig.is_debug_mode() else LogLevel.DEBUG),
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


def create_platform_specific_error_message(
    error: Exception, platform_name: str, context: Optional[dict[str, Any]] = None
) -> str:
    """プラットフォーム固有のエラーメッセージを作成"""
    from .platform_detector import check_module_availability, detect_platform

    platform_info = detect_platform()
    base_message = str(error)

    # プラットフォーム固有のエラーメッセージ拡張
    platform_specific_info = []
    troubleshooting_steps = []

    if platform_name == "windows":
        if "fcntl" in base_message.lower():
            platform_specific_info.append(
                "Windows環境では fcntl モジュールは利用できません。代替として msvcrt モジュールを使用してください。"
            )
            # msvcrtの可用性をチェック
            msvcrt_info = check_module_availability("msvcrt")
            if not msvcrt_info["available"]:
                troubleshooting_steps.append("msvcrtモジュールも利用できません。フォールバック機構を使用します。")

        if "permission" in base_message.lower():
            platform_specific_info.append(
                "Windows環境では管理者権限が必要な場合があります。PowerShellを管理者として実行してください。"
            )
            troubleshooting_steps.append(
                "1. PowerShellを右クリックして「管理者として実行」を選択\n"
                "2. Set-ExecutionPolicy RemoteSigned を実行\n"
                "3. 再度コマンドを実行"
            )

        if "path" in base_message.lower() or "command not found" in base_message.lower():
            platform_specific_info.append("Windows環境でPATHの問題が発生している可能性があります。")
            troubleshooting_steps.append(
                "PowerShellで $env:PATH を確認し、必要なディレクトリが含まれているか確認してください。"
            )

    elif platform_name == "macos":
        if "command not found" in base_message.lower():
            missing_tool = context.get("missing_tool", "required-tool") if context else "required-tool"
            platform_specific_info.append(
                f"macOS環境では Homebrew を使用してツールをインストールしてください: brew install {missing_tool}"
            )
            troubleshooting_steps.append(
                "1. Homebrewがインストールされているか確認: brew --version\n"
                '2. インストールされていない場合: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n'
                f"3. ツールをインストール: brew install {missing_tool}"
            )

        if "permission" in base_message.lower():
            platform_specific_info.append("macOS環境では、セキュリティ設定により実行が制限される場合があります。")
            troubleshooting_steps.append("システム環境設定 > セキュリティとプライバシー で実行を許可してください。")

    elif platform_name == "linux":
        if "command not found" in base_message.lower():
            missing_tool = context.get("missing_tool", "required-tool") if context else "required-tool"
            platform_specific_info.append(
                "Linux環境では apt または snap を使用して"
                f"ツールをインストールしてください: "
                f"sudo apt install {missing_tool}"
            )
            troubleshooting_steps.append(
                f"1. パッケージリストを更新: sudo apt update\n"
                f"2. ツールをインストール: sudo apt install {missing_tool}\n"
                f"3. 代替: sudo snap install {missing_tool}"
            )

        if "permission" in base_message.lower():
            platform_specific_info.append("Linux環境では sudo 権限が必要な場合があります。")

    elif platform_name == "wsl":
        if "windows" in base_message.lower():
            platform_specific_info.append(
                "WSL環境では Windows と Linux の両方のパスが混在する場合があります。適切なパス形式を使用してください。"
            )
            troubleshooting_steps.append(
                "1. wslpath コマンドでパス変換を確認\n"
                "2. /mnt/c/ 形式のWindowsパスを使用\n"
                "3. Linux形式のパス（/home/user/）を使用"
            )

    # CI環境固有の情報を追加
    if LoggingConfig.is_ci_environment():
        platform_specific_info.append(f"CI環境（{os.environ.get('GITHUB_ACTIONS', 'Unknown CI')}）で実行中です。")

        # GitHub Actions固有のトラブルシューティング
        if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            troubleshooting_steps.append(
                "GitHub Actions環境でのトラブルシューティング:\n"
                "1. ワークフローファイルの runs-on を確認\n"
                "2. setup-uv アクションのバージョンを確認\n"
                "3. PATH設定が正しく行われているか確認"
            )

    # エラーメッセージを構築
    enhanced_message = f"[{platform_info.display_name}] {base_message}"

    if platform_specific_info:
        enhanced_message += "\n\nプラットフォーム固有の情報:\n"
        for info in platform_specific_info:
            enhanced_message += f"  • {info}\n"

    if troubleshooting_steps:
        enhanced_message += "\nトラブルシューティング手順:\n"
        for step in troubleshooting_steps:
            enhanced_message += f"  {step}\n"

    # 推奨パッケージマネージャー情報を追加
    if platform_info.package_managers:
        enhanced_message += f"\n推奨パッケージマネージャー: {platform_info.package_managers[0]}"

    # CI環境では追加の診断情報を含める
    if LoggingConfig.is_ci_environment() and context:
        enhanced_message += f"\n\nCI診断情報: {context}"

    return enhanced_message


def get_platform_debug_info() -> dict[str, Any]:
    """プラットフォーム固有のデバッグ情報を取得"""
    from .platform_detector import detect_platform, get_available_package_managers

    platform_info = detect_platform()
    available_managers = get_available_package_managers(platform_info)

    return {
        "platform": {
            "name": platform_info.name,
            "display_name": platform_info.display_name,
            "shell": platform_info.shell,
            "python_cmd": platform_info.python_cmd,
            "supported_package_managers": platform_info.package_managers,
            "available_package_managers": available_managers,
        },
        "system": {
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "platform_machine": platform.machine(),
            "platform_processor": platform.processor(),
            "platform_node": platform.node(),
        },
        "environment": {
            "path": os.environ.get("PATH", ""),
            "home": os.environ.get("HOME", os.environ.get("USERPROFILE", "")),
            "shell": os.environ.get("SHELL", ""),
            "term": os.environ.get("TERM", ""),
        },
    }


# 後方互換性のためのエイリアス
__all__ = [
    "LoggingConfig",
    "setup_project_logging",
    "setup_ci_logging",
    "setup_development_logging",
    "setup_testing_logging",
    "create_platform_specific_error_message",
    "get_platform_debug_info",
    # ハンドラー（後方互換性）
    "create_ci_handler",
    "create_development_handler",
    "create_testing_handler",
]

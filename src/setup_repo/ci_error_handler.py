"""
CI/CD専用エラーハンドリングとレポート機能

このモジュールは、CI/CDパイプラインでの失敗時に
詳細なエラー報告とデバッグ情報を提供します。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .ci_environment import CIEnvironmentInfo
from .quality_errors import ErrorReporter
from .quality_logger import (
    LogLevel,
    QualityLogger,
    get_quality_logger,
)

# 後方互換性のためのエイリアス
__all__ = [
    "CIErrorHandler",
    "create_ci_error_handler",
    # CI環境情報（後方互換性）
    "CIEnvironmentInfo",
]


class CIErrorHandler:
    """CI/CD専用エラーハンドリングクラス"""

    def __init__(
        self,
        logger: Optional[QualityLogger] = None,
        enable_github_annotations: bool = True,
        error_report_dir: Optional[Path] = None,
    ):
        """
        CI/CDエラーハンドラーを初期化

        Args:
            logger: 使用するロガー（Noneの場合はデフォルトロガーを使用）
            enable_github_annotations: GitHub Actionsアノテーションを有効にするか
            error_report_dir: エラーレポート出力ディレクトリ
        """
        self.logger = logger or get_quality_logger()
        self.enable_github_annotations = enable_github_annotations
        self.error_report_dir = error_report_dir or Path("ci-error-reports")
        self.errors: list[Exception] = []

        # 統一されたエラーレポーターを初期化
        self.error_reporter = ErrorReporter(self.error_report_dir)

        # CI環境情報を収集
        self.ci_info = CIEnvironmentInfo.get_ci_metadata()
        self.system_info = CIEnvironmentInfo.get_system_info()
        self.dependency_info = CIEnvironmentInfo.get_dependency_info()

    def handle_stage_error(
        self,
        stage: str,
        error: Exception,
        duration: Optional[float] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """CI/CDステージエラーを処理"""
        self.errors.append(error)

        # プラットフォーム固有のエラーメッセージを作成
        from .logging_config import (
            create_platform_specific_error_message,
            get_platform_debug_info,
        )
        from .platform_detector import detect_platform

        platform_info = detect_platform()
        enhanced_error_message = create_platform_specific_error_message(error, platform_info.name, context)

        # ログに記録
        self.logger.log_ci_stage_failure(stage, error, duration)

        # GitHub Actionsアノテーションを出力（プラットフォーム情報付き）
        if self.enable_github_annotations and self._is_github_actions():
            annotation_message = f"[{platform_info.display_name}] Stage '{stage}' failed: {str(error)}"
            self._output_github_annotation("error", annotation_message)

        # 詳細なエラー情報をログ（プラットフォーム情報を含む）
        platform_debug_info = get_platform_debug_info()
        error_context = {
            "stage": stage,
            "duration": duration,
            "enhanced_error_message": enhanced_error_message,
            "platform_debug_info": platform_debug_info,
            "ci_info": self.ci_info,
            "system_info": self.system_info,
            **(context or {}),
        }

        self.logger.log_error_with_context(error, error_context)

    def handle_quality_check_error(
        self,
        check_type: str,
        error: Exception,
        metrics: Optional[dict[str, Any]] = None,
    ) -> None:
        """品質チェックエラーを処理"""
        self.errors.append(error)

        # プラットフォーム固有のエラーメッセージを作成
        from .logging_config import (
            create_platform_specific_error_message,
            get_platform_debug_info,
        )
        from .platform_detector import detect_platform

        platform_info = detect_platform()
        context = {"check_type": check_type, "metrics": metrics}
        enhanced_error_message = create_platform_specific_error_message(error, platform_info.name, context)

        # ログに記録
        self.logger.log_quality_check_failure(check_type, error, metrics)

        # GitHub Actionsアノテーションを出力（プラットフォーム情報付き）
        if self.enable_github_annotations and self._is_github_actions():
            annotation_message = f"[{platform_info.display_name}] Quality check '{check_type}' failed: {str(error)}"
            self._output_github_annotation("error", annotation_message)

        # プラットフォーム固有の詳細情報をログに追加
        platform_debug_info = get_platform_debug_info()
        self.logger.log_error_with_context(
            error,
            {
                "check_type": check_type,
                "enhanced_error_message": enhanced_error_message,
                "platform_debug_info": platform_debug_info,
                "metrics": metrics,
            },
        )

        # 品質チェック固有の詳細情報
        if hasattr(error, "details") and error.details:
            self._handle_quality_check_details(check_type, error.details)

    def _handle_quality_check_details(self, check_type: str, details: dict[str, Any]) -> None:
        """品質チェックの詳細情報を処理"""
        if check_type.lower() == "ruff" and "issues" in details:
            for issue in details["issues"][:5]:  # 最初の5つのみ表示
                if self.enable_github_annotations and self._is_github_actions():
                    file_path = issue.get("filename", "unknown")
                    line = issue.get("location", {}).get("row", 1)
                    message = issue.get("message", "Ruff issue")
                    self._output_github_annotation("warning", message, file_path, line)

        elif check_type.lower() == "mypy" and "errors" in details:
            for error_msg in details["errors"][:5]:  # 最初の5つのみ表示
                if self.enable_github_annotations and self._is_github_actions():
                    self._output_github_annotation("warning", f"MyPy: {error_msg}")

        elif check_type.lower() == "tests" and "failed_tests" in details:
            for test in details["failed_tests"][:5]:  # 最初の5つのみ表示
                if self.enable_github_annotations and self._is_github_actions():
                    self._output_github_annotation("error", f"Test failed: {test}")

    def create_comprehensive_error_report(self) -> dict[str, Any]:
        """包括的なエラーレポートを作成"""
        from .logging_config import get_platform_debug_info

        platform_debug_info = get_platform_debug_info()

        report: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "ci_environment": self.ci_info,
            "system_info": self.system_info,
            "dependency_info": self.dependency_info,
            "platform_debug_info": platform_debug_info,
            "total_errors": len(self.errors),
            "errors": [],
        }

        for error in self.errors:
            error_entry = {
                "type": type(error).__name__,
                "message": str(error),
                "timestamp": getattr(error, "timestamp", datetime.now().isoformat()),
            }

            if hasattr(error, "error_code"):
                error_entry["code"] = error.error_code

            if hasattr(error, "details"):
                error_entry["details"] = error.details

            # プラットフォーム固有のエラー情報を追加
            if hasattr(error, "platform_context"):
                error_entry["platform_context"] = error.platform_context

            report["errors"].append(error_entry)

        return report

    def save_error_report(self, filename: Optional[str] = None) -> Path:
        """エラーレポートをファイルに保存"""
        report = self.create_comprehensive_error_report()

        if filename:
            output_file = self.error_reporter.get_report_path(filename)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.logger.info(f"CI/CDエラーレポートを保存しました: {output_file}")
        else:
            output_file = self.error_reporter.save_report(report, "ci")

        # GitHub Actionsの場合、アーティファクトとしてアップロード可能にする
        if self._is_github_actions():
            self._output_github_annotation("notice", f"Error report saved: {output_file}")

        return output_file

    def generate_failure_summary(self) -> str:
        """失敗サマリーを生成"""
        if not self.errors:
            return "エラーは発生していません。"

        from .logging_config import get_platform_debug_info
        from .platform_detector import detect_platform

        platform_info = detect_platform()
        platform_debug_info = get_platform_debug_info()

        summary_lines = [
            f"## CI/CD失敗サマリー ({len(self.errors)}件のエラー)",
            "",
            f"**実行時刻:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**プラットフォーム:** {platform_info.display_name} ({platform_info.name})",
            f"**リポジトリ:** {self.ci_info.get('github_repository', 'unknown')}",
            f"**ブランチ:** {self.system_info.get('git_info', {}).get('branch', 'unknown')}",
            f"**コミット:** {self.system_info.get('git_info', {}).get('commit', 'unknown')[:8]}",
            "",
            "### プラットフォーム情報:",
            f"- **シェル:** {platform_info.shell}",
            f"- **Pythonコマンド:** {platform_info.python_cmd}",
            f"- **システム:** {platform_debug_info['system']['platform_system']} "
            f"{platform_debug_info['system']['platform_release']}",
            f"- **アーキテクチャ:** {platform_debug_info['system']['platform_machine']}",
            "",
            "### エラー詳細:",
            "",
        ]

        for i, error in enumerate(self.errors, 1):
            summary_lines.append(f"**{i}. {type(error).__name__}**")
            summary_lines.append(f"   - メッセージ: {str(error)}")

            if hasattr(error, "error_code"):
                summary_lines.append(f"   - エラーコード: {error.error_code}")

            if hasattr(error, "details") and error.details:
                summary_lines.append(f"   - 詳細: {json.dumps(error.details, ensure_ascii=False)}")

            # プラットフォーム固有の推奨事項を追加
            if "fcntl" in str(error).lower() and platform_info.name == "windows":
                summary_lines.append("   - **推奨事項:** Windows環境では msvcrt モジュールを使用してください")
            elif "command not found" in str(error).lower():
                if platform_info.name == "macos":
                    summary_lines.append("   - **推奨事項:** `brew install <tool>` でツールをインストールしてください")
                elif platform_info.name in ["linux", "wsl"]:
                    summary_lines.append(
                        "   - **推奨事項:** `sudo apt install <tool>` または "
                        "`sudo snap install <tool>` でツールをインストールしてください"
                    )

            summary_lines.append("")

        return "\n".join(summary_lines)

    def output_github_step_summary(self) -> None:
        """GitHub ActionsのStep Summaryに出力"""
        if not self._is_github_actions():
            return

        summary_file = os.getenv("GITHUB_STEP_SUMMARY")
        if not summary_file:
            return

        summary = self.generate_failure_summary()

        try:
            with open(summary_file, "a", encoding="utf-8") as f:
                f.write(summary)
                f.write("\n")

            self.logger.info("GitHub Step Summaryに失敗サマリーを出力しました")

        except Exception as e:
            self.logger.error(f"GitHub Step Summary出力エラー: {str(e)}")

    def _is_github_actions(self) -> bool:
        """GitHub Actions環境かどうかを判定"""
        return CIEnvironmentInfo.detect_ci_environment() == "github_actions"

    def _output_github_annotation(
        self,
        level: str,
        message: str,
        file_path: Optional[str] = None,
        line: Optional[int] = None,
    ) -> None:
        """GitHub Actionsアノテーションを出力"""
        if not self._is_github_actions():
            return

        annotation = f"::{level}"

        if file_path:
            annotation += f" file={file_path}"

        if line:
            annotation += f",line={line}"

        annotation += f"::{message}"

        print(annotation)

    def set_exit_code(self, exit_code: int = 1) -> None:
        """終了コードを設定してプロセスを終了"""
        if self.errors:
            # エラーレポートを保存
            self.save_error_report()

            # GitHub Step Summaryに出力
            self.output_github_step_summary()

            self.logger.critical(f"CI/CDパイプラインが失敗しました。終了コード: {exit_code}")

        sys.exit(exit_code)


def create_ci_error_handler(
    enable_github_annotations: bool = True,
    error_report_dir: Optional[Path] = None,
    log_level: LogLevel = LogLevel.INFO,
) -> CIErrorHandler:
    """CI/CDエラーハンドラーを作成"""
    # CI環境用のロガーを設定
    log_file = None
    if error_report_dir:
        log_file = error_report_dir / "ci.log"

    # 新しいロガーインスタンスを作成（シングルトンを使わない）
    from .quality_logger import QualityLogger

    logger = QualityLogger(
        name="setup_repo.ci",
        log_level=log_level,
        log_file=log_file,
        enable_console=True,
        enable_json_format=os.getenv("CI_JSON_LOGS", "").lower() == "true",
    )

    return CIErrorHandler(
        logger=logger,
        enable_github_annotations=enable_github_annotations,
        error_report_dir=error_report_dir,
    )

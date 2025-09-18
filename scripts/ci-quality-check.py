#!/usr/bin/env python3
"""
CI/CD品質チェックスクリプト

このスクリプトは、CI/CD環境で品質チェックを実行し、
失敗時に詳細なエラー報告を行います。
"""

import sys
import time
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# ruff: noqa: E402
from setup_repo.ci_error_handler import create_ci_error_handler
from setup_repo.logging_config import LoggingConfig, setup_ci_logging
from setup_repo.quality_metrics import QualityMetricsCollector


def main():
    """メイン実行関数"""
    # 環境に応じたロギングを設定
    logger = setup_ci_logging()

    # デバッグ情報をログ出力
    if LoggingConfig.is_debug_mode():
        debug_context = LoggingConfig.get_debug_context()
        logger.debug(f"デバッグコンテキスト: {debug_context}")

    # CI/CDエラーハンドラーを作成
    error_handler = create_ci_error_handler(
        enable_github_annotations=True,
        error_report_dir=Path("ci-reports"),
        log_level=LoggingConfig.get_log_level_from_env(),
    )

    try:
        error_handler.logger.info("CI/CD品質チェックを開始します")
        start_time = time.time()

        # プラットフォーム診断を実行
        from setup_repo.platform_detector import PlatformDetector

        detector = PlatformDetector()
        if detector.is_ci_environment():
            error_handler.logger.info("CI環境でのプラットフォーム診断を実行します")
            diagnosis = detector.diagnose_issues()

            # 診断結果をログ出力
            platform_info = detector.get_platform_info()
            platform_name = platform_info.display_name
            error_handler.logger.info(f"検出されたプラットフォーム: {platform_name}")

            # パッケージマネージャーの状態をチェック
            available_managers = [m for m, info in diagnosis["package_managers"].items() if info["available"]]

            if available_managers:
                managers_list = ", ".join(available_managers)
                error_handler.logger.info(f"利用可能なパッケージマネージャー: {managers_list}")
            else:
                error_handler.logger.warning("利用可能なパッケージマネージャーが見つかりません")

            # PATH関連の問題があれば警告
            if diagnosis["path_issues"]:
                for issue in diagnosis["path_issues"]:
                    error_handler.logger.warning(f"PATH問題: {issue}")

        # 品質メトリクス収集を実行
        collector = QualityMetricsCollector(project_root=project_root, logger=error_handler.logger)

        # 並列実行設定を取得
        import os

        parallel_workers = os.environ.get("PYTEST_XDIST_WORKER_COUNT", "auto")

        # CI環境変数を設定
        os.environ["CI"] = "true"
        os.environ["PYTEST_CURRENT_TEST"] = "ci-quality-check"  # テスト環境フラグ
        # CI環境では単体テストのみ実行（安定性と速度を優先）
        os.environ["SKIP_INTEGRATION_TESTS"] = "true"  # 統合テストをスキップ
        os.environ["UNIT_TESTS_ONLY"] = "true"  # 単体テストのみ実行
        # テストマーカーでパフォーマンステストと統合テストを除外
        os.environ["PYTEST_MARKERS"] = "unit and not performance and not stress and not integration"

        # 各品質チェックを段階的に実行（並列実行対応）
        stages = [
            ("Ruff Linting", collector.collect_ruff_metrics),
            ("MyPy Type Check", collector.collect_mypy_metrics),
            (
                "Test Execution",
                lambda: collector.collect_test_metrics(
                    parallel_workers=parallel_workers,
                    coverage_threshold=70.0,  # CI環境では70%を維持
                    skip_integration_tests=True,  # CI環境では単体テストのみ
                ),
            ),
            ("Security Scan", collector.collect_security_metrics),
        ]

        failed_stages = []

        for stage_name, stage_func in stages:
            stage_start = time.time()
            error_handler.logger.log_ci_stage_start(stage_name)

            try:
                result = stage_func()
                stage_duration = time.time() - stage_start

                if result.get("success", False):
                    error_handler.logger.log_ci_stage_success(stage_name, stage_duration)
                else:
                    # ステージ固有のエラーを作成
                    from setup_repo.quality_errors import QualityCheckError

                    error_details = {
                        "stage": stage_name,
                        "result": result,
                        "duration": stage_duration,
                    }

                    stage_error = QualityCheckError(
                        f"品質チェックステージ '{stage_name}' が失敗しました",
                        f"{stage_name.upper()}_FAILED",
                        error_details,
                    )

                    error_handler.handle_stage_error(stage_name, stage_error, stage_duration)
                    failed_stages.append(stage_name)

            except Exception as e:
                stage_duration = time.time() - stage_start
                error_handler.handle_stage_error(stage_name, e, stage_duration)
                failed_stages.append(stage_name)

        # 全体の実行時間を計算
        total_duration = time.time() - start_time

        if failed_stages:
            error_handler.logger.critical(
                f"品質チェックが失敗しました。失敗ステージ: {', '.join(failed_stages)} "
                f"(実行時間: {total_duration:.2f}秒)"
            )

            # 失敗サマリーを出力
            error_handler.output_github_step_summary()

            # 終了コード1で終了
            error_handler.set_exit_code(1)
        else:
            error_handler.logger.info(f"すべての品質チェックが成功しました (実行時間: {total_duration:.2f}秒)")

            # 全体メトリクスを収集して保存
            try:
                all_metrics = collector.collect_all_metrics()
                report_file = collector.save_metrics_report(all_metrics)
                error_handler.logger.info(f"品質レポートを保存しました: {report_file}")

            except Exception as e:
                error_handler.logger.warning(f"品質レポート保存エラー: {str(e)}")

    except Exception as e:
        # 予期しないエラーをキャッチ
        error_handler.handle_stage_error("Initialization", e)
        error_handler.set_exit_code(2)


if __name__ == "__main__":
    main()

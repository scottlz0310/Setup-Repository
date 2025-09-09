#!/usr/bin/env python3
"""品質メトリクス収集スクリプト

このスクリプトは品質メトリクスを収集し、レポートを生成します。
CI/CDパイプラインや開発者のローカル環境で使用できます。
"""

import argparse
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from setup_repo.quality_metrics import QualityLogger, QualityMetricsCollector


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="品質メトリクス収集スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/quality-metrics.py                    # 基本的な品質メトリクス収集
  python scripts/quality-metrics.py --output report.json  # 出力ファイル指定
  python scripts/quality-metrics.py --fail-on-error    # 品質基準未達成時に終了コード1
  python scripts/quality-metrics.py --verbose          # 詳細ログ出力
        """,
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root,
        help="プロジェクトルートディレクトリ（デフォルト: スクリプトの親ディレクトリ）",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="レポート出力ファイル（デフォルト: quality-report.json）",
    )

    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="品質基準を満たさない場合に終了コード1で終了",
    )

    parser.add_argument(
        "--min-coverage",
        type=float,
        default=80.0,
        help="最低カバレッジ要件（デフォルト: 80.0）",
    )

    parser.add_argument("--verbose", action="store_true", help="詳細ログ出力")

    parser.add_argument(
        "--format",
        choices=["json", "text", "github"],
        default="text",
        help="出力形式（デフォルト: text）",
    )

    args = parser.parse_args()

    # ロガー設定
    logger = QualityLogger()
    if args.verbose:
        logger.logger.setLevel("DEBUG")

    try:
        # メトリクス収集
        collector = QualityMetricsCollector(args.project_root)
        metrics = collector.collect_all_metrics()

        # レポート保存
        output_file = args.output or (args.project_root / "quality-report.json")
        report_file = collector.save_metrics_report(metrics, output_file)

        # 結果出力
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "quality_score": metrics.get_quality_score(),
                        "metrics": {
                            "test_coverage": metrics.test_coverage,
                            "ruff_issues": metrics.ruff_issues,
                            "mypy_errors": metrics.mypy_errors,
                            "security_vulnerabilities": metrics.security_vulnerabilities,
                            "test_passed": metrics.test_passed,
                            "test_failed": metrics.test_failed,
                        },
                        "passing": metrics.is_passing(args.min_coverage),
                        "report_file": str(report_file),
                    },
                    indent=2,
                )
            )

        elif args.format == "github":
            # GitHub Actions用の出力
            print(f"::set-output name=quality_score::{metrics.get_quality_score():.1f}")
            print(f"::set-output name=coverage::{metrics.test_coverage:.1f}")
            print(f"::set-output name=ruff_issues::{metrics.ruff_issues}")
            print(f"::set-output name=mypy_errors::{metrics.mypy_errors}")
            print(
                f"::set-output name=security_vulnerabilities::{metrics.security_vulnerabilities}"
            )
            print(
                f"::set-output name=passing::{'true' if metrics.is_passing(args.min_coverage) else 'false'}"
            )

        else:  # text format
            print("\n" + "=" * 60)
            print("📊 品質メトリクスレポート")
            print("=" * 60)
            print(f"品質スコア: {metrics.get_quality_score():.1f}/100")
            print(f"テストカバレッジ: {metrics.test_coverage:.1f}%")
            print(f"Ruffエラー: {metrics.ruff_issues}件")
            print(f"MyPyエラー: {metrics.mypy_errors}件")
            print(f"セキュリティ脆弱性: {metrics.security_vulnerabilities}件")
            print(f"テスト成功: {metrics.test_passed}件")
            print(f"テスト失敗: {metrics.test_failed}件")
            print(f"コミットハッシュ: {metrics.commit_hash}")
            print(f"タイムスタンプ: {metrics.timestamp}")
            print(f"レポートファイル: {report_file}")
            print("-" * 60)

            if metrics.is_passing(args.min_coverage):
                print("✅ 品質基準を満たしています")
            else:
                print("❌ 品質基準を満たしていません")

                # 具体的な問題を表示
                issues = []
                if metrics.ruff_issues > 0:
                    issues.append(f"Ruffエラー: {metrics.ruff_issues}件")
                if metrics.mypy_errors > 0:
                    issues.append(f"MyPyエラー: {metrics.mypy_errors}件")
                if metrics.test_coverage < args.min_coverage:
                    issues.append(
                        f"カバレッジ不足: {metrics.test_coverage:.1f}% < {args.min_coverage}%"
                    )
                if metrics.test_failed > 0:
                    issues.append(f"テスト失敗: {metrics.test_failed}件")
                if metrics.security_vulnerabilities > 0:
                    issues.append(
                        f"セキュリティ脆弱性: {metrics.security_vulnerabilities}件"
                    )

                print("\n問題:")
                for issue in issues:
                    print(f"  - {issue}")

        # 品質基準チェック
        if args.fail_on_error and not metrics.is_passing(args.min_coverage):
            sys.exit(1)

    except Exception as e:
        logger.logger.error(f"品質メトリクス収集エラー: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

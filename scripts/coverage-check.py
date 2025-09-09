#!/usr/bin/env python3
"""
カバレッジチェックスクリプト

このスクリプトは以下の機能を提供します：
- カバレッジ測定の実行
- 品質ゲートのチェック
- カバレッジレポートの生成
- 未カバー行の分析
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CoverageChecker:
    """カバレッジチェッククラス"""

    def __init__(self, min_coverage: float = 80.0):
        self.min_coverage = min_coverage
        self.project_root = Path(__file__).parent.parent
        self.coverage_file = self.project_root / "coverage.json"
        self.html_dir = self.project_root / "htmlcov"

    def run_tests_with_coverage(self) -> bool:
        """カバレッジ付きでテストを実行"""
        print("🧪 カバレッジ付きテスト実行中...")

        cmd = [
            "uv",
            "run",
            "pytest",
            "tests/",
            "--cov=src/setup_repo",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-report=json",
            "--cov-report=xml",
            f"--cov-fail-under={self.min_coverage}",
            "-v",
        ]

        try:
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, check=False
            )

            print(result.stdout)
            if result.stderr:
                print("エラー出力:", result.stderr)

            return result.returncode == 0
        except Exception as e:
            print(f"❌ テスト実行エラー: {e}")
            return False

    def get_coverage_data(self) -> Optional[Dict]:
        """カバレッジデータを取得"""
        try:
            if not self.coverage_file.exists():
                print("❌ カバレッジファイルが見つかりません")
                return None

            with open(self.coverage_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ カバレッジデータ読み込みエラー: {e}")
            return None

    def analyze_coverage(self) -> Tuple[bool, Dict]:
        """カバレッジを分析"""
        coverage_data = self.get_coverage_data()
        if not coverage_data:
            return False, {}

        total_coverage = coverage_data["totals"]["percent_covered"]

        analysis = {
            "total_coverage": total_coverage,
            "passes_gate": total_coverage >= self.min_coverage,
            "lines_covered": coverage_data["totals"]["covered_lines"],
            "lines_missing": coverage_data["totals"]["missing_lines"],
            "total_lines": coverage_data["totals"]["num_statements"],
            "files": {},
        }

        # ファイル別分析
        for file_path, file_data in coverage_data["files"].items():
            if "src/setup_repo" in file_path:
                file_coverage = file_data["summary"]["percent_covered"]
                analysis["files"][file_path] = {
                    "coverage": file_coverage,
                    "missing_lines": file_data["missing_lines"],
                    "covered_lines": file_data["summary"]["covered_lines"],
                    "total_lines": file_data["summary"]["num_statements"],
                }

        return True, analysis

    def generate_report(self, analysis: Dict) -> str:
        """カバレッジレポートを生成"""
        report = []
        report.append("=" * 60)
        report.append("📊 カバレッジレポート")
        report.append("=" * 60)

        # 全体サマリー
        total_cov = analysis["total_coverage"]
        status = "✅ 通過" if analysis["passes_gate"] else "❌ 未達成"

        report.append(f"\n🎯 品質ゲート ({self.min_coverage}%): {status}")
        report.append(f"📈 全体カバレッジ: {total_cov:.2f}%")
        report.append(f"📝 総行数: {analysis['total_lines']}")
        report.append(f"✅ カバー済み: {analysis['lines_covered']}")
        report.append(f"❌ 未カバー: {analysis['lines_missing']}")

        # ファイル別詳細
        report.append("\n" + "=" * 40)
        report.append("📁 ファイル別カバレッジ")
        report.append("=" * 40)

        sorted_files = sorted(analysis["files"].items(), key=lambda x: x[1]["coverage"])

        for file_path, file_data in sorted_files:
            file_name = Path(file_path).name
            coverage = file_data["coverage"]
            status_icon = "✅" if coverage >= self.min_coverage else "❌"

            report.append(f"\n{status_icon} {file_name}: {coverage:.1f}%")

            if file_data["missing_lines"] and coverage < self.min_coverage:
                missing = file_data["missing_lines"][:10]  # 最初の10行のみ表示
                missing_str = ", ".join(map(str, missing))
                if len(file_data["missing_lines"]) > 10:
                    missing_str += f" ... (+{len(file_data['missing_lines']) - 10}行)"
                report.append(f"   未カバー行: {missing_str}")

        return "\n".join(report)

    def check_coverage_trend(self, previous_coverage: Optional[float] = None) -> str:
        """カバレッジトレンドをチェック"""
        if previous_coverage is None:
            return "📊 トレンド分析: 前回データなし"

        success, analysis = self.analyze_coverage()
        if not success:
            return "❌ トレンド分析: 現在のカバレッジデータ取得失敗"

        current_coverage = analysis["total_coverage"]
        diff = current_coverage - previous_coverage

        if diff > 0:
            return f"📈 トレンド: +{diff:.2f}% (改善)"
        elif diff < 0:
            return f"📉 トレンド: {diff:.2f}% (低下)"
        else:
            return "📊 トレンド: 変化なし"

    def suggest_improvements(self, analysis: Dict) -> List[str]:
        """改善提案を生成"""
        suggestions = []

        # 低カバレッジファイルの特定
        low_coverage_files = [
            (path, data)
            for path, data in analysis["files"].items()
            if data["coverage"] < self.min_coverage
        ]

        if low_coverage_files:
            suggestions.append("🎯 改善提案:")
            suggestions.append("")

            for file_path, file_data in sorted(
                low_coverage_files, key=lambda x: x[1]["coverage"]
            ):
                file_name = Path(file_path).name
                coverage = file_data["coverage"]
                missing_count = len(file_data["missing_lines"])

                suggestions.append(f"• {file_name} ({coverage:.1f}%)")
                suggestions.append(f"  - {missing_count}行の追加テストが必要")

                if missing_count <= 5:
                    missing_lines = ", ".join(map(str, file_data["missing_lines"]))
                    suggestions.append(f"  - 未カバー行: {missing_lines}")

        return suggestions

    def run_quality_gate(self) -> bool:
        """品質ゲートを実行"""
        print("🚀 カバレッジ品質ゲート実行中...")

        # テスト実行
        test_success = self.run_tests_with_coverage()
        if not test_success:
            print("❌ テスト実行に失敗しました")
            return False

        # カバレッジ分析
        success, analysis = self.analyze_coverage()
        if not success:
            print("❌ カバレッジ分析に失敗しました")
            return False

        # レポート生成
        report = self.generate_report(analysis)
        print(report)

        # 改善提案
        suggestions = self.suggest_improvements(analysis)
        if suggestions:
            print("\n" + "\n".join(suggestions))

        # HTMLレポートの場所を表示
        if self.html_dir.exists():
            html_report = self.html_dir / "index.html"
            print(f"\n📊 詳細なHTMLレポート: {html_report}")

        return analysis["passes_gate"]


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="カバレッジチェックツール")
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=80.0,
        help="最低カバレッジ要件 (デフォルト: 80.0)",
    )
    parser.add_argument(
        "--previous-coverage", type=float, help="前回のカバレッジ（トレンド分析用）"
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="テスト実行をスキップしてレポートのみ生成",
    )

    args = parser.parse_args()

    checker = CoverageChecker(min_coverage=args.min_coverage)

    if args.report_only:
        # レポートのみ生成
        success, analysis = checker.analyze_coverage()
        if success:
            report = checker.generate_report(analysis)
            print(report)

            if args.previous_coverage:
                trend = checker.check_coverage_trend(args.previous_coverage)
                print(f"\n{trend}")

            sys.exit(0 if analysis["passes_gate"] else 1)
        else:
            print("❌ カバレッジデータが見つかりません")
            sys.exit(1)
    else:
        # 品質ゲート実行
        success = checker.run_quality_gate()

        if args.previous_coverage:
            trend = checker.check_coverage_trend(args.previous_coverage)
            print(f"\n{trend}")

        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

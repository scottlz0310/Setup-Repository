#!/usr/bin/env python3
"""
カバレッジ監視システム

このモジュールは、テストカバレッジの監視、レポート生成、アラート機能を提供します。
品質ゲートの一部として、カバレッジ要件のチェックと継続的な監視を行います。
"""

import json
import logging
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CoverageReport:
    """カバレッジレポートのデータモデル"""

    total_coverage: float
    module_coverage: dict[str, float]
    missing_lines: dict[str, list[int]]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "total_coverage": self.total_coverage,
            "module_coverage": self.module_coverage,
            "missing_lines": self.missing_lines,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CoverageTarget:
    """カバレッジ目標の設定"""

    total_target: float = 80.0
    module_target: float = 60.0
    critical_module_target: float = 80.0

    # 重要なモジュール（より高いカバレッジが必要）
    critical_modules: list[str] = None

    def __post_init__(self):
        if self.critical_modules is None:
            self.critical_modules = [
                "setup_repo.cli",
                "setup_repo.config",
                "setup_repo.setup",
                "setup_repo.sync",
                "setup_repo.git_operations",
                "setup_repo.github_api",
            ]


class CoverageMonitor:
    """カバレッジ監視システムのメインクラス"""

    def __init__(self, project_root: Path | None = None):
        """
        カバレッジ監視システムを初期化

        Args:
            project_root: プロジェクトルートディレクトリ
        """
        self.project_root = project_root or Path.cwd()
        self.coverage_dir = self.project_root / "htmlcov"
        self.reports_dir = self.project_root / "coverage-reports"
        self.reports_dir.mkdir(exist_ok=True)

        # ログ設定
        self.logger = self._setup_logging()

        # カバレッジ目標設定
        self.targets = CoverageTarget()

    def _setup_logging(self) -> logging.Logger:
        """ログ設定を初期化"""
        logger = logging.getLogger("coverage_monitor")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def run_coverage_tests(self) -> bool:
        """
        カバレッジ付きでテストを実行

        Returns:
            カバレッジファイルが生成されたかどうか
        """
        self.logger.info("カバレッジ付きテストを実行中...")

        try:
            # uvを使用してテストを実行
            cmd = [
                "uv",
                "run",
                "pytest",
                "--cov=src/setup_repo",
                "--cov-report=xml:coverage.xml",
                "--cov-report=html:htmlcov",
                "--cov-report=json:coverage.json",
                "--cov-report=term-missing",
                "--continue-on-collection-errors",  # コレクションエラーでも継続
            ]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分でタイムアウト
            )

            # テストの成功/失敗に関係なく、カバレッジファイルが生成されたかをチェック
            coverage_files = [self.project_root / "coverage.xml", self.project_root / "coverage.json"]

            coverage_generated = any(f.exists() for f in coverage_files)

            if result.returncode == 0:
                self.logger.info("テスト実行が成功しました")
                return True
            elif coverage_generated:
                self.logger.warning(
                    f"テストで失敗がありましたが、カバレッジレポートは生成されました (終了コード: {result.returncode})"
                )
                if result.stderr:
                    self.logger.debug(f"テスト実行時の警告: {result.stderr}")
                return True
            else:
                self.logger.error(f"テスト実行が失敗し、カバレッジファイルも生成されませんでした: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("テスト実行がタイムアウトしました")
            return False
        except Exception as e:
            self.logger.error(f"テスト実行中にエラーが発生しました: {e}")
            return False

    def parse_coverage_xml(self) -> CoverageReport | None:
        """
        coverage.xmlファイルを解析してカバレッジレポートを生成

        Returns:
            カバレッジレポート、または解析に失敗した場合はNone
        """
        xml_path = self.project_root / "coverage.xml"

        if not xml_path.exists():
            self.logger.error("coverage.xmlファイルが見つかりません")
            return None

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # 全体のカバレッジを取得
            total_coverage = float(root.attrib.get("line-rate", 0)) * 100

            # モジュール別カバレッジを取得
            module_coverage = {}
            missing_lines = {}

            for package in root.findall(".//package"):
                for class_elem in package.findall("classes/class"):
                    filename = class_elem.attrib.get("filename", "")
                    line_rate = float(class_elem.attrib.get("line-rate", 0)) * 100

                    # モジュール名を生成
                    if filename.startswith("src/setup_repo/"):
                        module_name = filename.replace("src/", "").replace("/", ".").replace(".py", "")
                        module_coverage[module_name] = line_rate

                        # 欠落行を取得
                        missing = []
                        for line in class_elem.findall("lines/line"):
                            if line.attrib.get("hits", "0") == "0":
                                missing.append(int(line.attrib.get("number", 0)))
                        missing_lines[module_name] = missing

            return CoverageReport(
                total_coverage=total_coverage,
                module_coverage=module_coverage,
                missing_lines=missing_lines,
                timestamp=datetime.now(tz=None),
            )

        except Exception as e:
            self.logger.error(f"coverage.xmlの解析中にエラーが発生しました: {e}")
            return None

    def parse_coverage_json(self) -> CoverageReport | None:
        """
        coverage.jsonファイルを解析してカバレッジレポートを生成

        Returns:
            カバレッジレポート、または解析に失敗した場合はNone
        """
        json_path = self.project_root / "coverage.json"

        if not json_path.exists():
            self.logger.warning("coverage.jsonファイルが見つかりません")
            return None

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

            # 全体のカバレッジを取得
            totals = data.get("totals", {})
            total_coverage = totals.get("percent_covered", 0)

            # モジュール別カバレッジを取得
            module_coverage = {}
            missing_lines = {}

            files = data.get("files", {})
            for filepath, file_data in files.items():
                if filepath.startswith("src/setup_repo/"):
                    module_name = filepath.replace("src/", "").replace("/", ".").replace(".py", "")
                    summary = file_data.get("summary", {})
                    module_coverage[module_name] = summary.get("percent_covered", 0)

                    # 欠落行を取得
                    missing_lines[module_name] = file_data.get("missing_lines", [])

            return CoverageReport(
                total_coverage=total_coverage,
                module_coverage=module_coverage,
                missing_lines=missing_lines,
                timestamp=datetime.now(tz=None),
            )

        except Exception as e:
            self.logger.error(f"coverage.jsonの解析中にエラーが発生しました: {e}")
            return None

    def check_coverage_requirements(self, report: CoverageReport) -> tuple[bool, list[str]]:
        """
        カバレッジ要件をチェック

        Args:
            report: カバレッジレポート

        Returns:
            (要件を満たしているか, 警告メッセージのリスト)
        """
        warnings = []
        passed = True

        # 全体カバレッジのチェック
        if report.total_coverage < self.targets.total_target:
            warnings.append(
                f"全体カバレッジが目標を下回っています: {report.total_coverage:.2f}% < {self.targets.total_target}%"
            )
            passed = False

        # モジュール別カバレッジのチェック
        for module, coverage in report.module_coverage.items():
            target = (
                self.targets.critical_module_target
                if module in self.targets.critical_modules
                else self.targets.module_target
            )

            if coverage < target:
                warnings.append(
                    f"モジュール '{module}' のカバレッジが目標を下回っています: {coverage:.2f}% < {target}%"
                )
                if module in self.targets.critical_modules:
                    passed = False

        return passed, warnings

    def generate_coverage_report(self) -> dict[str, Any] | None:
        """
        包括的なカバレッジレポートを生成

        Returns:
            レポートデータ、または生成に失敗した場合はNone
        """
        self.logger.info("カバレッジレポートを生成中...")

        # テストを実行
        if not self.run_coverage_tests():
            return None

        # カバレッジデータを解析
        report = self.parse_coverage_json() or self.parse_coverage_xml()
        if not report:
            return None

        # 要件チェック
        passed, warnings = self.check_coverage_requirements(report)

        # レポートデータを構築
        report_data = {
            "timestamp": datetime.now(tz=None).isoformat(),
            "coverage": report.to_dict(),
            "requirements_check": {
                "passed": passed,
                "warnings": warnings,
                "targets": asdict(self.targets),
            },
            "summary": {
                "total_modules": len(report.module_coverage),
                "modules_above_target": sum(
                    1 for coverage in report.module_coverage.values() if coverage >= self.targets.module_target
                ),
                "critical_modules_above_target": sum(
                    1
                    for module, coverage in report.module_coverage.items()
                    if module in self.targets.critical_modules and coverage >= self.targets.critical_module_target
                ),
            },
        }

        # レポートファイルを保存
        report_file = self.reports_dir / f"coverage_report_{datetime.now(tz=None).strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"カバレッジレポートを保存しました: {report_file}")

        return report_data

    def send_coverage_alert(self, coverage: float, warnings: list[str]) -> None:
        """
        カバレッジアラートを送信

        Args:
            coverage: 現在のカバレッジ
            warnings: 警告メッセージのリスト
        """
        self.logger.warning(f"カバレッジアラート: 現在のカバレッジ {coverage:.2f}%")

        for warning in warnings:
            self.logger.warning(f"  - {warning}")

        # 将来的にはSlack、メール、GitHub Issueなどへの通知を実装可能
        # 現在はログ出力のみ

        # アラートファイルを作成（CI/CDで検出可能）
        alert_file = self.project_root / "coverage_alert.txt"
        with open(alert_file, "w", encoding="utf-8") as f:
            f.write(f"カバレッジアラート - {datetime.now(tz=None).isoformat()}\n")
            f.write(f"現在のカバレッジ: {coverage:.2f}%\n")
            f.write("警告:\n")
            for warning in warnings:
                f.write(f"  - {warning}\n")

    def update_coverage_badge(self, coverage: float) -> None:
        """
        カバレッジバッジを更新

        Args:
            coverage: 現在のカバレッジ
        """
        # バッジの色を決定
        if coverage >= 90:
            color = "brightgreen"
        elif coverage >= 80:
            color = "green"
        elif coverage >= 70:
            color = "yellow"
        elif coverage >= 60:
            color = "orange"
        else:
            color = "red"

        # バッジ情報をファイルに保存（GitHub Actionsで使用）
        badge_data = {
            "schemaVersion": 1,
            "label": "coverage",
            "message": f"{coverage:.1f}%",
            "color": color,
        }

        badge_file = self.project_root / "coverage_badge.json"
        with open(badge_file, "w", encoding="utf-8") as f:
            json.dump(badge_data, f, indent=2)

        self.logger.info(f"カバレッジバッジを更新しました: {coverage:.1f}% ({color})")

    def get_historical_coverage(self, days: int = 30) -> list[dict[str, Any]]:
        """
        過去のカバレッジデータを取得

        Args:
            days: 取得する日数

        Returns:
            過去のカバレッジデータのリスト
        """
        historical_data = []

        # レポートファイルを日付順でソート
        report_files = sorted(
            self.reports_dir.glob("coverage_report_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        cutoff_time = datetime.now(tz=None).timestamp() - (days * 24 * 3600)

        for report_file in report_files:
            if report_file.stat().st_mtime < cutoff_time:
                break

            try:
                with open(report_file, encoding="utf-8") as f:
                    data = json.load(f)
                historical_data.append(data)
            except Exception as e:
                self.logger.warning(f"レポートファイルの読み込みに失敗: {report_file} - {e}")

        return historical_data

    def analyze_coverage_trends(self) -> dict[str, Any]:
        """
        カバレッジトレンドを分析

        Returns:
            トレンド分析結果
        """
        historical_data = self.get_historical_coverage()

        if len(historical_data) < 2:
            return {"error": "トレンド分析には最低2つのデータポイントが必要です"}

        # 最新と最古のデータを比較
        latest = historical_data[0]
        oldest = historical_data[-1]

        latest_coverage = latest["coverage"]["total_coverage"]
        oldest_coverage = oldest["coverage"]["total_coverage"]

        trend = latest_coverage - oldest_coverage

        return {
            "period_days": len(historical_data),
            "latest_coverage": latest_coverage,
            "oldest_coverage": oldest_coverage,
            "trend": trend,
            "trend_direction": "improving" if trend > 0 else "declining" if trend < 0 else "stable",
            "data_points": len(historical_data),
        }


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="カバレッジ監視システム")
    parser.add_argument("--generate-report", action="store_true", help="カバレッジレポートを生成")
    parser.add_argument("--check-requirements", action="store_true", help="カバレッジ要件をチェック")
    parser.add_argument("--analyze-trends", action="store_true", help="カバレッジトレンドを分析")
    parser.add_argument("--project-root", type=Path, help="プロジェクトルートディレクトリ")

    args = parser.parse_args()

    monitor = CoverageMonitor(args.project_root)

    if args.generate_report:
        report_data = monitor.generate_coverage_report()
        if report_data:
            print("カバレッジレポートが正常に生成されました")

            # 要件チェック結果を表示
            req_check = report_data["requirements_check"]
            if not req_check["passed"]:
                print("⚠️  カバレッジ要件を満たしていません:")
                for warning in req_check["warnings"]:
                    print(f"  - {warning}")

                # アラートを送信（ただし終了はしない）
                monitor.send_coverage_alert(report_data["coverage"]["total_coverage"], req_check["warnings"])
                print("⚠️  警告: カバレッジ要件を満たしていませんが、レポートは生成されました")
            else:
                print("✅ カバレッジ要件を満たしています")

            # バッジを更新
            monitor.update_coverage_badge(report_data["coverage"]["total_coverage"])
        else:
            print("カバレッジレポートの生成に失敗しました")
            sys.exit(1)

    elif args.check_requirements:
        # 既存のカバレッジデータをチェック
        report = monitor.parse_coverage_json() or monitor.parse_coverage_xml()
        if report:
            passed, warnings = monitor.check_coverage_requirements(report)
            if passed:
                print("✅ カバレッジ要件を満たしています")
            else:
                print("⚠️  カバレッジ要件を満たしていません:")
                for warning in warnings:
                    print(f"  - {warning}")
                sys.exit(1)
        else:
            print("カバレッジデータが見つかりません")
            sys.exit(1)

    elif args.analyze_trends:
        trends = monitor.analyze_coverage_trends()
        if "error" in trends:
            print(f"エラー: {trends['error']}")
        else:
            print(f"カバレッジトレンド分析 ({trends['period_days']}日間):")
            print(f"  最新: {trends['latest_coverage']:.2f}%")
            print(f"  最古: {trends['oldest_coverage']:.2f}%")
            print(f"  変化: {trends['trend']:+.2f}% ({trends['trend_direction']})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

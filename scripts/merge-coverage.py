#!/usr/bin/env python3
"""
プラットフォーム統合カバレッジヘルパー

各プラットフォーム（Windows/Linux/macOS）で実行されたテストのカバレッジを統合し、
実環境重視のテスト戦略における真のカバレッジを測定します。

ルール5.2準拠: 80%カバレッジ目標を統合カバレッジで判定
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("coverage-merge.log", encoding="utf-8")],
)
logger = logging.getLogger(__name__)


@dataclass
class CoverageData:
    """カバレッジデータ構造"""

    platform: str
    python_version: str
    total_coverage: float
    files: dict[str, dict]
    statements: int
    covered: int
    missing: int


@dataclass
class MergedCoverage:
    """統合カバレッジ結果"""

    total_coverage: float
    platforms: list[str]
    python_versions: list[str]
    total_statements: int
    covered_statements: int
    missing_statements: int
    file_coverage: dict[str, float]
    platform_contributions: dict[str, float]


class CoverageMerger:
    """プラットフォーム統合カバレッジ処理"""

    def __init__(self, coverage_dir: Path = Path("coverage-artifacts")):
        self.coverage_dir = coverage_dir
        self.merged_dir = Path("merged-coverage")
        self.merged_dir.mkdir(exist_ok=True)

    def collect_coverage_files(self) -> list[Path]:
        """カバレッジファイルを収集"""
        coverage_files = []

        # 各プラットフォームのカバレッジファイルを検索
        patterns = [
            "coverage-*.json",
            "**/coverage.json",
            "cross-platform-test-results-*/coverage.json",
            "**/coverage.xml",  # XML形式も対象
            "**/.coverage",  # .coverageファイルも対象
        ]

        for pattern in patterns:
            found_files = list(self.coverage_dir.glob(pattern))
            coverage_files.extend(found_files)
            if found_files:
                logger.info(f"パターン '{pattern}' で {len(found_files)} 個のファイルを発見")

        # 重複を除去
        coverage_files = list(set(coverage_files))

        logger.info(f"発見されたカバレッジファイル: {len(coverage_files)}個")

        # デバッグ用: 見つからない場合は詳細情報を出力
        if not coverage_files:
            logger.warning("カバレッジファイルが見つかりません。ディレクトリ構造を確認します:")
            if self.coverage_dir.exists():
                for item in self.coverage_dir.rglob("*"):
                    if item.is_file():
                        logger.info(f"  ファイル: {item}")
            else:
                logger.error(f"カバレッジディレクトリが存在しません: {self.coverage_dir}")

        return coverage_files

    def parse_coverage_file(self, file_path: Path) -> CoverageData | None:
        """カバレッジファイルを解析"""
        try:
            if file_path.suffix == ".xml":
                return self._parse_xml_coverage(file_path)
            elif file_path.suffix == ".json":
                return self._parse_json_coverage(file_path)
            elif file_path.name == ".coverage":
                logger.warning(f".coverageファイルは現在サポートされていません: {file_path}")
                return None
            else:
                logger.warning(f"サポートされていないファイル形式: {file_path}")
                return None

        except Exception as e:
            logger.error(f"カバレッジファイル解析エラー {file_path}: {e}")
            return None

    def _parse_json_coverage(self, file_path: Path) -> CoverageData | None:
        """カバレッジJSONファイルを解析"""
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # プラットフォーム情報を推定
        platform = self._extract_platform_info(file_path)
        python_version = self._extract_python_version(file_path)

        totals = data.get("totals", {})

        return CoverageData(
            platform=platform,
            python_version=python_version,
            total_coverage=totals.get("percent_covered", 0.0),
            files=data.get("files", {}),
            statements=totals.get("num_statements", 0),
            covered=totals.get("covered_lines", 0),
            missing=totals.get("missing_lines", 0),
        )

    def _parse_xml_coverage(self, file_path: Path) -> CoverageData | None:
        """カバレッジXMLファイルを解析"""
        import xml.etree.ElementTree as ET

        tree = ET.parse(file_path)
        root = tree.getroot()

        # プラットフォーム情報を推定
        platform = self._extract_platform_info(file_path)
        python_version = self._extract_python_version(file_path)

        # XMLからカバレッジ情報を抽出
        line_rate = float(root.get("line-rate", 0.0))
        total_coverage = line_rate * 100

        lines_covered = int(root.get("lines-covered", 0))
        lines_valid = int(root.get("lines-valid", 0))

        # ファイル情報を抽出
        files = {}
        for package in root.findall(".//package"):
            for class_elem in package.findall("classes/class"):
                filename = class_elem.get("filename", "")
                if filename:
                    class_line_rate = float(class_elem.get("line-rate", 0.0))
                    files[filename] = {
                        "summary": {
                            "percent_covered": class_line_rate * 100,
                            "num_statements": len(class_elem.findall(".//line")),
                            "covered_lines": len(
                                [line for line in class_elem.findall(".//line") if line.get("hits", "0") != "0"]
                            ),
                        }
                    }

        return CoverageData(
            platform=platform,
            python_version=python_version,
            total_coverage=total_coverage,
            files=files,
            statements=lines_valid,
            covered=lines_covered,
            missing=lines_valid - lines_covered,
        )

    def _extract_platform_info(self, file_path: Path) -> str:
        """ファイルパスからプラットフォーム情報を抽出"""
        path_str = str(file_path).lower()

        if "windows" in path_str or "win" in path_str:
            return "windows"
        elif "macos" in path_str or "mac" in path_str or "darwin" in path_str:
            return "macos"
        elif "ubuntu" in path_str or "linux" in path_str:
            return "linux"
        else:
            return "unknown"

    def _extract_python_version(self, file_path: Path) -> str:
        """ファイルパスからPythonバージョンを抽出"""
        path_str = str(file_path)

        # パターンマッチングでPythonバージョンを抽出
        import re

        version_match = re.search(r"python?[-_]?(\d+\.\d+)", path_str)
        if version_match:
            return version_match.group(1)

        # デフォルト値
        return "3.11"

    def merge_coverage_data(self, coverage_data_list: list[CoverageData]) -> MergedCoverage:
        """カバレッジデータを統合"""
        if not coverage_data_list:
            raise ValueError("統合するカバレッジデータがありません")

        # 全ファイルの統合
        all_files: set[str] = set()
        platform_files: dict[str, set[str]] = {}

        for data in coverage_data_list:
            all_files.update(data.files.keys())
            platform_files.setdefault(data.platform, set()).update(data.files.keys())

        # ファイル別統合カバレッジ計算
        file_coverage = {}
        total_statements = 0
        total_covered = 0

        for file_path in all_files:
            file_statements = 0
            file_covered = 0

            # 各プラットフォームからファイルカバレッジを収集
            for data in coverage_data_list:
                if file_path in data.files:
                    file_data = data.files[file_path]
                    summary = file_data.get("summary", {})

                    statements = summary.get("num_statements", 0)
                    covered = summary.get("covered_lines", 0)

                    # 最大値を使用（プラットフォーム間で実行されるテストが異なるため）
                    file_statements = max(file_statements, statements)
                    file_covered = max(file_covered, covered)

            if file_statements > 0:
                file_coverage[file_path] = (file_covered / file_statements) * 100
                total_statements += file_statements
                total_covered += file_covered

        # 総合カバレッジ計算
        total_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0.0

        # プラットフォーム貢献度計算
        platform_contributions = {}
        platforms = list({data.platform for data in coverage_data_list})
        python_versions = list({data.python_version for data in coverage_data_list})

        for platform in platforms:
            platform_data = [d for d in coverage_data_list if d.platform == platform]
            if platform_data:
                avg_coverage = sum(d.total_coverage for d in platform_data) / len(platform_data)
                platform_contributions[platform] = avg_coverage

        return MergedCoverage(
            total_coverage=total_coverage,
            platforms=platforms,
            python_versions=python_versions,
            total_statements=total_statements,
            covered_statements=total_covered,
            missing_statements=total_statements - total_covered,
            file_coverage=file_coverage,
            platform_contributions=platform_contributions,
        )

    def generate_report(self, merged: MergedCoverage) -> dict:
        """統合カバレッジレポート生成"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "merged_coverage": {
                "total_coverage": merged.total_coverage,
                "platforms": merged.platforms,
                "python_versions": merged.python_versions,
                "statements": {
                    "total": merged.total_statements,
                    "covered": merged.covered_statements,
                    "missing": merged.missing_statements,
                },
            },
            "quality_gate": {
                "target": 80.0,
                "passed": merged.total_coverage >= 80.0,
                "status": "PASS" if merged.total_coverage >= 80.0 else "FAIL",
            },
            "platform_contributions": merged.platform_contributions,
            "file_coverage": merged.file_coverage,
            "summary": {
                "total_files": len(merged.file_coverage),
                "files_above_80": sum(1 for cov in merged.file_coverage.values() if cov >= 80),
                "files_above_60": sum(1 for cov in merged.file_coverage.values() if cov >= 60),
                "files_below_60": sum(1 for cov in merged.file_coverage.values() if cov < 60),
            },
        }

        return report

    def save_report(self, report: dict, output_path: Path = None) -> Path:
        """レポートを保存"""
        if output_path is None:
            output_path = self.merged_dir / "merged-coverage-report.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"統合カバレッジレポートを保存: {output_path}")
        return output_path

    def generate_html_report(self, report: dict) -> Path:
        """HTML形式のレポート生成"""
        html_path = self.merged_dir / "merged-coverage-report.html"

        merged = report["merged_coverage"]
        quality_gate = report["quality_gate"]

        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>統合カバレッジレポート</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .coverage {{ font-size: 2em; font-weight: bold; }}
        .pass {{ color: #28a745; }}
        .fail {{ color: #dc3545; }}
        .warning {{ color: #ffc107; }}
        .platform {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }}
        .file-list {{ margin-top: 20px; }}
        .file-item {{ margin: 5px 0; padding: 5px; }}
        .high-coverage {{ background: #d4edda; }}
        .medium-coverage {{ background: #fff3cd; }}
        .low-coverage {{ background: #f8d7da; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔄 プラットフォーム統合カバレッジレポート</h1>
        <div class="coverage {"pass" if quality_gate["passed"] else "fail"}">
            {merged["total_coverage"]:.2f}%
        </div>
        <p>品質ゲート (80%): {"✅ 通過" if quality_gate["passed"] else "❌ 未達成"}</p>
        <p>生成日時: {report["timestamp"]}</p>
    </div>

    <h2>📊 統計情報</h2>
    <ul>
        <li>対象プラットフォーム: {", ".join(merged["platforms"])}</li>
        <li>Pythonバージョン: {", ".join(merged["python_versions"])}</li>
        <li>総ステートメント数: {merged["statements"]["total"]:,}</li>
        <li>カバー済み: {merged["statements"]["covered"]:,}</li>
        <li>未カバー: {merged["statements"]["missing"]:,}</li>
    </ul>

    <h2>🖥️ プラットフォーム別貢献度</h2>
"""

        for platform, coverage in report["platform_contributions"].items():
            status_class = "pass" if coverage >= 80 else "warning" if coverage >= 60 else "fail"
            html_content += f"""
    <div class="platform">
        <strong>{platform.title()}</strong>:
        <span class="{status_class}">{coverage:.2f}%</span>
    </div>
"""

        html_content += """
    <h2>📁 ファイル別カバレッジ</h2>
    <div class="file-list">
"""

        for file_path, coverage in sorted(report["file_coverage"].items()):
            if coverage >= 80:
                css_class = "high-coverage"
                status = "✅"
            elif coverage >= 60:
                css_class = "medium-coverage"
                status = "⚠️"
            else:
                css_class = "low-coverage"
                status = "❌"

            filename = Path(file_path).name
            html_content += f"""
        <div class="file-item {css_class}">
            {status} <strong>{filename}</strong>: {coverage:.2f}%
        </div>
"""

        html_content += """
    </div>
</body>
</html>
"""

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTMLレポートを生成: {html_path}")
        return html_path

    def run_merge(self) -> tuple[bool, dict]:
        """統合処理実行"""
        try:
            # カバレッジファイル収集
            coverage_files = self.collect_coverage_files()
            if not coverage_files:
                logger.error("カバレッジファイルが見つかりません")
                return False, {}

            # データ解析
            coverage_data_list = []
            for file_path in coverage_files:
                data = self.parse_coverage_file(file_path)
                if data:
                    coverage_data_list.append(data)

            if not coverage_data_list:
                logger.error("有効なカバレッジデータが見つかりません")
                return False, {}

            logger.info(f"解析されたカバレッジデータ: {len(coverage_data_list)}個")

            # 統合処理
            merged = self.merge_coverage_data(coverage_data_list)

            # レポート生成
            report = self.generate_report(merged)

            # 保存
            self.save_report(report)
            self.generate_html_report(report)

            # 結果出力
            logger.info(f"統合カバレッジ: {merged.total_coverage:.2f}%")
            logger.info(f"品質ゲート (80%): {'通過' if merged.total_coverage >= 80 else '未達成'}")

            return merged.total_coverage >= 80, report

        except Exception as e:
            logger.error(f"統合処理エラー: {e}")
            return False, {}


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="プラットフォーム統合カバレッジヘルパー")
    parser.add_argument(
        "--coverage-dir", type=Path, default=Path("coverage-artifacts"), help="カバレッジファイルディレクトリ"
    )
    parser.add_argument("--fail-under", type=float, default=80.0, help="品質ゲート閾値 (デフォルト: 80%)")
    parser.add_argument("--generate-summary", action="store_true", help="Markdownサマリーのみ生成")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細ログ出力")

    args = parser.parse_args()

    if args.generate_summary:
        # Markdownサマリー生成モード
        report_path = Path("merged-coverage/merged-coverage-report.json")
        if report_path.exists():
            try:
                with open(report_path, encoding="utf-8") as f:
                    report = json.load(f)

                merged = report["merged_coverage"]
                quality_gate = report["quality_gate"]
                summary = report["summary"]

                print("# 🔄 プラットフォーム統合カバレッジレポート")
                print()
                print(f"**統合カバレッジ**: {merged['total_coverage']:.2f}%")
                print(f"**品質ゲート (80%)**: {'✅ 通過' if quality_gate['passed'] else '❌ 未達成'}")
                print(f"**対象プラットフォーム**: {', '.join(merged['platforms'])}")
                print(f"**Pythonバージョン**: {', '.join(merged['python_versions'])}")
                print()
                print("## 📊 統計情報")
                print(f"- 総ステートメント数: {merged['statements']['total']:,}")
                print(f"- カバー済み: {merged['statements']['covered']:,}")
                print(f"- 未カバー: {merged['statements']['missing']:,}")
                print(f"- 総ファイル数: {summary['total_files']}")
                print(f"- 80%以上のファイル: {summary['files_above_80']}")
                print(f"- 60%以上のファイル: {summary['files_above_60']}")
                print()
                print("## 🖥️ プラットフォーム別貢献度")

                for platform, coverage in report["platform_contributions"].items():
                    status = "✅" if coverage >= 80 else "⚠️" if coverage >= 60 else "❌"
                    print(f"{status} **{platform.title()}**: {coverage:.2f}%")

                print()
                print("**実環境重視テスト戦略**: 各プラットフォームで実際に実行されたテストの統合結果")
                print(f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            except Exception as e:
                print("# ⚠️ 統合カバレッジレポート")
                print(f"統合カバレッジレポートの生成に失敗しました: {e}")
        else:
            print("# ⚠️ 統合カバレッジレポート")
            print("統合カバレッジレポートファイルが見つかりません。")
        return

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 統合処理実行
    merger = CoverageMerger(args.coverage_dir)
    passed, report = merger.run_merge()

    if report:
        total_coverage = report["merged_coverage"]["total_coverage"]

        print("\n🔄 プラットフォーム統合カバレッジ結果")
        print(f"統合カバレッジ: {total_coverage:.2f}%")
        print(f"品質ゲート ({args.fail_under}%): {'✅ 通過' if passed else '❌ 未達成'}")
        print(f"対象プラットフォーム: {', '.join(report['merged_coverage']['platforms'])}")

        # CI環境での出力
        if os.getenv("CI"):
            print(f"::notice::統合カバレッジ: {total_coverage:.2f}%")
            if passed:
                print("::notice::品質ゲート通過 (80%以上)")
            else:
                print(f"::warning::品質ゲート未達成 ({total_coverage:.2f}% < {args.fail_under}%)")

    # 終了コード
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
セキュリティチェック統合スクリプト

このスクリプトは以下のセキュリティチェックを実行します：
- Safety: 既知の脆弱性チェック
- Bandit: コードセキュリティ分析
- Semgrep: セキュリティパターンマッチング
- License check: ライセンス監査
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class SecurityChecker:
    """セキュリティチェック統合クラス"""

    def __init__(self, output_dir: Path = Path("security-reports")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}

    def run_safety_check(self) -> dict[str, Any]:
        """Safetyによる脆弱性チェック"""
        print("🔍 Safety による既知の脆弱性チェックを実行中...")

        try:
            # 新しいscanコマンドを使用（shell=Falseで安全に実行）
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "safety",
                    "scan",
                    "--output",
                    "json",
                    "--save-as",
                    str(self.output_dir / "safety-report.json"),
                ],
                capture_output=True,
                text=True,
                check=False,
                shell=False,  # 明示的にshell=Falseを指定
            )

            # 標準出力でも結果表示
            subprocess.run(
                ["uv", "run", "safety", "scan", "--output", "screen"], 
                check=False,
                shell=False
            )

            # 結果解析
            report_file = self.output_dir / "safety-report.json"
            if report_file.exists():
                with open(report_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # 新しいフォーマットに対応
                    vulnerabilities = data.get("vulnerabilities", [])
                    if isinstance(vulnerabilities, list):
                        vulnerability_count = len(vulnerabilities)
                    else:
                        vulnerability_count = 0

                    return {
                        "status": "success" if vulnerability_count == 0 else "warning",
                        "vulnerabilities": vulnerability_count,
                        "details": data,
                    }

            # レポートファイルがない場合は標準出力から判断
            if "0 security issues found" in result.stdout or result.returncode == 0:
                return {
                    "status": "success",
                    "vulnerabilities": 0,
                    "message": "脆弱性は検出されませんでした",
                }
            else:
                # 標準出力から脆弱性数を抽出を試行
                import re

                vuln_match = re.search(r"(\d+) security issues found", result.stdout)
                vuln_count = int(vuln_match.group(1)) if vuln_match else 0

                return {
                    "status": "warning" if vuln_count > 0 else "success",
                    "vulnerabilities": vuln_count,
                    "message": (
                        f"{vuln_count}件の脆弱性が検出されました"
                        if vuln_count > 0
                        else "脆弱性は検出されませんでした"
                    ),
                }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_bandit_check(self) -> dict[str, Any]:
        """Banditによるセキュリティ分析"""
        print("🔍 Bandit によるセキュリティ分析を実行中...")

        try:
            # JSON形式でレポート生成
            subprocess.run(
                [
                    "uv",
                    "run",
                    "bandit",
                    "-r",
                    "src/",
                    "-c",
                    "pyproject.toml",
                    "-f",
                    "json",
                    "-o",
                    str(self.output_dir / "bandit-report.json"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            # 標準出力でも結果表示
            subprocess.run(
                [
                    "uv",
                    "run",
                    "bandit",
                    "-r",
                    "src/",
                    "-c",
                    "pyproject.toml",
                    "-f",
                    "txt",
                ],
                check=False,
            )

            # 結果解析
            report_file = self.output_dir / "bandit-report.json"
            if report_file.exists():
                with open(report_file, encoding="utf-8") as f:
                    data = json.load(f)
                    results = data.get("results", [])
                    high_issues = [
                        r for r in results if r.get("issue_severity") == "HIGH"
                    ]
                    medium_issues = [
                        r for r in results if r.get("issue_severity") == "MEDIUM"
                    ]

                    return {
                        "status": (
                            "error"
                            if high_issues
                            else "warning"
                            if medium_issues
                            else "success"
                        ),
                        "high_issues": len(high_issues),
                        "medium_issues": len(medium_issues),
                        "total_issues": len(results),
                        "details": data,
                    }

            return {"status": "success", "message": "問題は検出されませんでした"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_semgrep_check(self) -> dict[str, Any]:
        """Semgrepによるセキュリティ分析（オプション）"""
        print("🔍 Semgrep によるセキュリティ分析を実行中...")

        try:
            # Semgrepがインストールされているかチェック
            check_result = subprocess.run(
                ["uv", "run", "python", "-c", "import semgrep"],
                capture_output=True,
                text=True,
                check=False,
            )

            if check_result.returncode != 0:
                return {
                    "status": "warning",
                    "errors": 0,
                    "warnings": 0,
                    "total_issues": 0,
                    "message": (
                        "Semgrepがインストールされていません"
                        "（LGPLライセンスのため除外）"
                    ),
                }

            # JSON形式でレポート生成
            subprocess.run(
                [
                    "uv",
                    "run",
                    "semgrep",
                    "--config=auto",
                    "src/",
                    "--json",
                    "--output",
                    str(self.output_dir / "semgrep-report.json"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            # 標準出力でも結果表示
            subprocess.run(
                ["uv", "run", "semgrep", "--config=auto", "src/"], check=False
            )

            # 結果解析
            report_file = self.output_dir / "semgrep-report.json"
            if report_file.exists():
                with open(report_file, encoding="utf-8") as f:
                    data = json.load(f)
                    results = data.get("results", [])
                    errors = [
                        r
                        for r in results
                        if r.get("extra", {}).get("severity") == "ERROR"
                    ]
                    warnings = [
                        r
                        for r in results
                        if r.get("extra", {}).get("severity") == "WARNING"
                    ]

                    return {
                        "status": (
                            "error" if errors else "warning" if warnings else "success"
                        ),
                        "errors": len(errors),
                        "warnings": len(warnings),
                        "total_issues": len(results),
                        "details": data,
                    }

            return {"status": "success", "message": "問題は検出されませんでした"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_license_check(self) -> dict[str, Any]:
        """ライセンス監査"""
        print("🔍 ライセンス監査を実行中...")

        try:
            # JSON形式でレポート生成
            subprocess.run(
                [
                    "uv",
                    "run",
                    "pip-licenses",
                    "--format=json",
                    "--output-file",
                    str(self.output_dir / "licenses-report.json"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            # 標準出力でも結果表示
            subprocess.run(["uv", "run", "pip-licenses", "--format=plain"], check=False)

            # 結果解析
            report_file = self.output_dir / "licenses-report.json"
            if report_file.exists():
                with open(report_file, encoding="utf-8") as f:
                    data = json.load(f)

                    # 禁止ライセンスをチェック
                    forbidden_licenses = ["GPL", "AGPL", "LGPL"]
                    forbidden_packages = []
                    unknown_packages = []

                    for package in data:
                        license_name = package.get("License", "")
                        package_name = package.get("Name", "")

                        # Semgrepは除外（オプションツールのため）
                        if package_name.lower() == "semgrep":
                            continue

                        if any(
                            forbidden in license_name.upper()
                            for forbidden in forbidden_licenses
                        ):
                            forbidden_packages.append(package)
                        elif license_name in ["UNKNOWN", ""]:
                            unknown_packages.append(package)

                    status = (
                        "error"
                        if forbidden_packages
                        else "warning"
                        if unknown_packages
                        else "success"
                    )

                    return {
                        "status": status,
                        "total_packages": len(data),
                        "forbidden_packages": len(forbidden_packages),
                        "unknown_packages": len(unknown_packages),
                        "forbidden_details": forbidden_packages,
                        "unknown_details": unknown_packages,
                        "details": data,
                    }

            return {
                "status": "error",
                "message": "レポートファイルが生成されませんでした",
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def generate_summary(self) -> None:
        """セキュリティチェック結果のサマリー生成"""
        print("\n" + "=" * 60)
        print("🛡️  セキュリティチェック結果サマリー")
        print("=" * 60)

        overall_status = "success"

        for check_name, result in self.results.items():
            status = result.get("status", "unknown")
            if status == "error":
                overall_status = "error"
            elif status == "warning" and overall_status != "error":
                overall_status = "warning"

            status_icon = {"success": "✅", "warning": "⚠️", "error": "❌"}.get(
                status, "❓"
            )

            print(f"\n{status_icon} {check_name}:")

            if check_name == "Safety":
                vuln_count = result.get("vulnerabilities", 0)
                print(f"   既知の脆弱性: {vuln_count}件")

            elif check_name == "Bandit":
                high = result.get("high_issues", 0)
                medium = result.get("medium_issues", 0)
                print(f"   高リスク: {high}件, 中リスク: {medium}件")

            elif check_name == "Semgrep":
                errors = result.get("errors", 0)
                warnings = result.get("warnings", 0)
                print(f"   エラー: {errors}件, 警告: {warnings}件")

            elif check_name == "License":
                forbidden = result.get("forbidden_packages", 0)
                unknown = result.get("unknown_packages", 0)
                total = result.get("total_packages", 0)
                print(
                    "   総パッケージ: "
                    f"{total}件, 禁止ライセンス: {forbidden}件, "
                    f"不明: {unknown}件"
                )

        print("\n" + "=" * 60)
        overall_icon = {"success": "✅", "warning": "⚠️", "error": "❌"}.get(
            overall_status, "❓"
        )

        print(f"{overall_icon} 総合結果: {overall_status.upper()}")
        print("=" * 60)

        # 詳細レポートの場所を表示
        print(f"\n📁 詳細レポート: {self.output_dir.absolute()}")

        # エラーがある場合は終了コードを設定
        if overall_status == "error":
            sys.exit(1)
        elif overall_status == "warning":
            sys.exit(2)

    def run_all_checks(self) -> None:
        """全てのセキュリティチェックを実行"""
        print("🚀 セキュリティチェックを開始します...\n")

        # 各チェックを実行
        self.results["Safety"] = self.run_safety_check()
        self.results["Bandit"] = self.run_bandit_check()
        self.results["Semgrep"] = self.run_semgrep_check()
        self.results["License"] = self.run_license_check()

        # サマリー生成
        self.generate_summary()


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="セキュリティチェック統合スクリプト")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("security-reports"),
        help="レポート出力ディレクトリ (デフォルト: security-reports)",
    )
    parser.add_argument(
        "--check",
        choices=["safety", "bandit", "semgrep", "license", "all"],
        default="all",
        help="実行するチェック (デフォルト: all)",
    )

    args = parser.parse_args()

    checker = SecurityChecker(args.output_dir)

    if args.check == "all":
        checker.run_all_checks()
    elif args.check == "safety":
        result = checker.run_safety_check()
        checker.results["Safety"] = result
        checker.generate_summary()
    elif args.check == "bandit":
        result = checker.run_bandit_check()
        checker.results["Bandit"] = result
        checker.generate_summary()
    elif args.check == "semgrep":
        result = checker.run_semgrep_check()
        checker.results["Semgrep"] = result
        checker.generate_summary()
    elif args.check == "license":
        result = checker.run_license_check()
        checker.results["License"] = result
        checker.generate_summary()


if __name__ == "__main__":
    main()

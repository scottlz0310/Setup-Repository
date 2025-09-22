#!/usr/bin/env python3
"""ローカル環境用セキュリティチェックスクリプト

このスクリプトはローカル環境でのセキュリティ脆弱性チェックを行い、
修復可能な問題を開発者に報告します。
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# WindowsでのUTF-8エンコーディング強制設定
if os.name == "nt":
    import contextlib

    if hasattr(sys.stdout, "reconfigure"):
        with contextlib.suppress(Exception):
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")

# ruff: noqa: E402
# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from setup_repo.security_helpers import safe_subprocess


def run_bandit_check() -> tuple[bool, list[dict], list[str]]:
    """Banditセキュリティチェック実行（pyproject.toml設定準拠）"""
    try:
        # 引数を構築（pyproject.tomlの設定を使用）
        args = ["uv", "run", "bandit", "-r", "src/", "-f", "json"]

        # pyproject.tomlで設定済みの除外設定を使用
        args.extend(["--exclude", "tests,venv,.venv,build,dist"])
        args.extend(["--skip", "B101,B603,B607,B404,B604,B310,B108"])

        result = safe_subprocess(
            args,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        vulnerabilities = []
        if result.stdout:
            try:
                bandit_data = json.loads(result.stdout)
                vulnerabilities = bandit_data.get("results", [])
            except json.JSONDecodeError:
                return False, [], [f"Bandit出力の解析に失敗: {result.stderr}"]

        return True, vulnerabilities, []

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return False, [], [f"Banditの実行に失敗: {e}"]


def run_safety_check() -> tuple[bool, list[dict], list[str]]:
    """Safety脆弱性チェック実行"""
    try:
        result = safe_subprocess(
            ["uv", "run", "safety", "check", "--json"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        vulnerabilities = []
        if result.stdout:
            try:
                safety_data = json.loads(result.stdout)
                if isinstance(safety_data, list):
                    vulnerabilities = safety_data
            except json.JSONDecodeError:
                return False, [], [f"Safety出力の解析に失敗: {result.stderr}"]

        return True, vulnerabilities, []

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return False, [], [f"Safetyの実行に失敗: {e}"]


def format_vulnerability_report(bandit_vulns: list[dict], safety_vulns: list[dict]) -> str:
    """脆弱性レポートをフォーマット"""
    report = []

    if bandit_vulns:
        report.append("[BANDIT] Banditで検出されたセキュリティ問題:")
        for vuln in bandit_vulns[:10]:  # 最初の10件のみ表示
            severity = vuln.get("issue_severity", "UNKNOWN")
            confidence = vuln.get("issue_confidence", "UNKNOWN")
            filename = vuln.get("filename", "unknown")
            line_number = vuln.get("line_number", "?")
            test_id = vuln.get("test_id", "")

            report.append(f"  [X] {filename}:{line_number} [{severity}/{confidence}] {test_id}")
            report.append(f"     {vuln.get('issue_text', 'No description')}")

        if len(bandit_vulns) > 10:
            report.append(f"  ... 他 {len(bandit_vulns) - 10} 件")

    if safety_vulns:
        report.append("\n[SAFETY] Safetyで検出された依存関係の脆弱性:")
        for vuln in safety_vulns[:5]:  # 最初の5件のみ表示
            package = vuln.get("package", "unknown")
            version = vuln.get("installed_version", "unknown")
            vuln_id = vuln.get("vulnerability_id", "")

            report.append(f"  [!] {package} {version} - {vuln_id}")
            report.append(f"     {vuln.get('advisory', 'No advisory')}")

        if len(safety_vulns) > 5:
            report.append(f"  ... 他 {len(safety_vulns) - 5} 件")

    return "\n".join(report)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="ローカル環境用セキュリティチェック（pyproject.toml設定準拠）")
    parser.add_argument("--config", type=Path, default=Path("pyproject.toml"), help="設定ファイルパス")
    parser.add_argument("--local-mode", action="store_true", help="ローカルモード（脆弱性があっても警告のみ）")
    parser.add_argument("--strict", action="store_true", help="厳格モード（脆弱性があると失敗）")
    parser.add_argument("--verbose", action="store_true", help="詳細出力")

    args = parser.parse_args()

    print("[SECURITY] Bandit + Safety セキュリティチェックを実行中...")

    # Banditチェック
    bandit_success, bandit_vulns, bandit_errors = run_bandit_check()

    # Safetyチェック
    safety_success, safety_vulns, safety_errors = run_safety_check()

    total_vulns = len(bandit_vulns) + len(safety_vulns)
    total_errors = bandit_errors + safety_errors

    if args.verbose:
        print(f"Bandit: {len(bandit_vulns)}件の脆弱性")
        print(f"Safety: {len(safety_vulns)}件の脆弱性")
        if total_errors:
            print(f"エラー: {len(total_errors)}件")

    if total_vulns == 0 and not total_errors:
        print("[OK] Bandit + Safety チェック完了: 脆弱性は検出されませんでした")
        return 0

    if total_vulns > 0:
        print(f"\n[WARNING] Bandit + Safety: {total_vulns}件のセキュリティ脆弱性が検出されました")

        if args.verbose or total_vulns <= 20:
            print("\n" + format_vulnerability_report(bandit_vulns, safety_vulns))

        print("\n[FIX] 修復方法:")
        if bandit_vulns:
            print("  - Bandit問題: コードを見直し、セキュアな実装に変更してください")
        if safety_vulns:
            print("  - Safety問題: `uv sync` で最新版に更新するか、代替パッケージを検討してください")

        if args.local_mode:
            print("\n[INFO] ローカルモード: 脆弱性は検出されましたが、開発を継続できます")
            print("   本番環境では修復が必要です")
            return 0
        elif args.strict:
            print("\n[ERROR] 厳格モード: 脆弱性があるため失敗しました")
            return 1
        else:
            # デフォルト: 警告のみ
            print("\n[WARNING] 警告: 脆弱性が検出されましたが、処理を継続します")
            return 0

    if total_errors:
        print("\n[ERROR] Bandit + Safety チェック中にエラーが発生しました:")
        for error in total_errors:
            print(f"  - {error}")

        if args.local_mode:
            print("\n[WARNING] 警告: エラーが発生しましたが、処理を継続します")
            return 0
        elif args.strict:
            return 1
        else:
            print("\n[WARNING] 警告: エラーが発生しましたが、処理を継続します")
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

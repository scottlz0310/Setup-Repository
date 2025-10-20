#!/usr/bin/env python3
"""CI環境でのプラットフォーム診断スクリプト.

このスクリプトは、CI環境でプラットフォーム関連の問題を
診断し、詳細な情報を出力します。
"""

import json
import os
import sys
from pathlib import Path

# Windows環境でのUnicodeEncodeError対策
# 環境変数でUTF-8エンコーディングを強制設定
os.environ["PYTHONIOENCODING"] = "utf-8"

# Windows環境での標準出力エンコーディング修正
if sys.platform == "win32":
    try:
        # Python 3.7以降のWindows環境でUTF-8モードを有効化
        import codecs

        # 標準出力・標準エラー出力をUTF-8に設定
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        else:
            # 古いPythonバージョン用のフォールバック
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    except Exception:
        # エンコーディング設定に失敗した場合は継続
        pass

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# ruff: noqa: E402
from setup_repo.platform_detector import PlatformDetector


def main():
    """メイン実行関数"""
    print("=== CI環境プラットフォーム診断（強化版） ===")

    detector = PlatformDetector()

    # 基本プラットフォーム情報
    print("\n1. プラットフォーム情報:")
    platform_info = detector.get_platform_info()
    print(f"  プラットフォーム: {platform_info.display_name}")
    print(f"  内部名: {platform_info.name}")
    print(f"  シェル: {platform_info.shell}")
    print(f"  Pythonコマンド: {platform_info.python_cmd}")
    print(f"  推奨パッケージマネージャー: {', '.join(platform_info.package_managers)}")

    # CI環境情報
    print("\n2. CI環境情報:")
    ci_info = detector.get_ci_info()
    important_keys = [
        "GITHUB_ACTIONS",
        "RUNNER_OS",
        "RUNNER_ARCH",
        "GITHUB_WORKFLOW",
        "platform_system",
        "platform_release",
        "python_version",
    ]

    for key in important_keys:
        if key in ci_info:
            print(f"  {key}: {ci_info[key]}")

    # その他の環境変数（最初の5つのみ）
    other_keys = [k for k in ci_info if k not in important_keys][:5]
    if other_keys:
        print("  その他の環境変数:")
        for key in other_keys:
            print(f"    {key}: {ci_info[key]}")

    # 診断結果
    print("\n3. 診断結果:")
    diagnosis = detector.diagnose_issues()

    print("  パッケージマネージャー状態:")
    for manager, status in diagnosis["package_managers"].items():
        available = "✅" if status["available"] else "❌"
        in_path = "✅" if status["in_path"] else "❌"
        print(f"    {manager}: 利用可能={available}, PATH内={in_path}")

    # モジュール可用性の状態
    if "module_availability" in diagnosis:
        print("  モジュール可用性:")
        for module_name, module_info in diagnosis["module_availability"].items():
            available = "✅" if module_info["available"] else "❌"
            platform_specific = "🔧" if module_info["platform_specific"] else "📦"
            print(f"    {platform_specific} {module_name}: {available}")

            if not module_info["available"] and module_info["import_error"]:
                print(f"      エラー: {module_info['import_error']}")

    # CI固有の問題
    if "ci_specific_issues" in diagnosis and diagnosis["ci_specific_issues"]:
        print("  CI固有の問題:")
        for issue in diagnosis["ci_specific_issues"]:
            print(f"    🚨 {issue}")

    if diagnosis["path_issues"]:
        print("  PATH関連の問題:")
        for issue in diagnosis["path_issues"]:
            print(f"    ⚠️  {issue}")

    if diagnosis["recommendations"]:
        print("  推奨事項:")
        for rec in diagnosis["recommendations"]:
            print(f"    💡 {rec}")

    # プラットフォーム固有の詳細診断
    print("\n4. プラットフォーム固有診断:")
    _perform_platform_specific_diagnostics(platform_info)

    # JSON形式でも出力（CI用）
    print("\n5. JSON診断データ:")
    json_data = {
        "platform": {
            "name": platform_info.name,
            "display_name": platform_info.display_name,
            "shell": platform_info.shell,
            "python_cmd": platform_info.python_cmd,
            "package_managers": platform_info.package_managers,
        },
        "ci_environment": {k: v for k, v in ci_info.items() if k in important_keys},
        "diagnosis": {
            "package_managers": diagnosis["package_managers"],
            "module_availability": diagnosis.get("module_availability", {}),
            "ci_specific_issues": diagnosis.get("ci_specific_issues", []),
            "path_issues": diagnosis["path_issues"],
            "recommendations": diagnosis["recommendations"],
        },
    }

    print(json.dumps(json_data, indent=2, ensure_ascii=False))

    # GitHub Actions用のアノテーション
    if detector.is_github_actions():
        print("\n6. GitHub Actionsアノテーション:")

        # precommit環境の検出
        if os.environ.get("PRE_COMMIT") == "1":
            print("::notice::precommit環境で実行中")

        # CI固有の問題を警告として出力
        if "ci_specific_issues" in diagnosis:
            for issue in diagnosis["ci_specific_issues"]:
                print(f"::warning::CI固有問題: {issue}")

        # PATH関連の問題を警告として出力（precommit環境では軽減）
        for issue in diagnosis["path_issues"]:
            if os.environ.get("PRE_COMMIT") == "1":
                print(f"::debug::PATH問題（precommit環境）: {issue}")
            else:
                print(f"::warning::PATH問題: {issue}")

        # エラーの出力
        if "error" in diagnosis and diagnosis["error"]:
            print(f"::error::診断エラー: {diagnosis['error']}")

        # 利用可能なパッケージマネージャーを情報として出力
        available_managers = [m for m, info in diagnosis["package_managers"].items() if info["available"]]
        if available_managers:
            managers_list = ", ".join(available_managers)
            print(f"::notice::利用可能なパッケージマネージャー: {managers_list}")
        else:
            print("::warning::利用可能なパッケージマネージャーが見つかりません")

        # プラットフォーム固有の情報を出力
        print(f"::notice::検出プラットフォーム: {platform_info.display_name}")

        # モジュール可用性の重要な情報を出力
        if "module_availability" in diagnosis:
            critical_modules = ["fcntl", "msvcrt"]
            for module_name in critical_modules:
                if module_name in diagnosis["module_availability"]:
                    module_info = diagnosis["module_availability"][module_name]
                    if module_info["platform_specific"]:
                        status = "利用可能" if module_info["available"] else "利用不可"
                        print(f"::debug::{module_name}モジュール: {status} (プラットフォーム固有)")

    # 診断結果に基づく終了コード判定
    print("\n7. 診断結果サマリー:")

    critical_issues = []
    warnings = []

    # 重大な問題をチェック
    if diagnosis.get("error"):
        critical_issues.append(f"診断エラー: {diagnosis['error']}")

    # 利用可能なパッケージマネージャーがない場合（precommit環境では軽減）
    available_managers = [m for m, info in diagnosis["package_managers"].items() if info["available"]]
    if not available_managers:
        if os.environ.get("PRE_COMMIT") == "1":
            warnings.append("利用可能なパッケージマネージャーが見つかりません（precommit環境）")
        else:
            critical_issues.append("利用可能なパッケージマネージャーが見つかりません")

    # CI固有の問題をチェック（precommit環境を考慮）
    if "ci_specific_issues" in diagnosis and diagnosis["ci_specific_issues"]:
        for issue in diagnosis["ci_specific_issues"]:
            if "一致しません" in issue:
                if os.environ.get("PRE_COMMIT") == "1":
                    warnings.append(f"{issue}（precommit環境）")
                else:
                    critical_issues.append(issue)
            else:
                warnings.append(issue)

    # PATH問題をチェック（precommit環境では軽減）
    if diagnosis["path_issues"]:
        if os.environ.get("PRE_COMMIT") == "1":
            # precommit環境ではPATH問題を軽減
            path_warnings = [f"{issue}（precommit環境）" for issue in diagnosis["path_issues"]]
            warnings.extend(path_warnings)
        else:
            warnings.extend(diagnosis["path_issues"])

    # 結果出力
    if critical_issues:
        print("❌ 重大な問題:")
        for issue in critical_issues:
            print(f"  • {issue}")

    if warnings:
        print("⚠️ 警告:")
        for warning in warnings:
            print(f"  • {warning}")

    if not critical_issues and not warnings:
        print("✅ 問題は検出されませんでした")

    # 終了コード決定
    if critical_issues:
        print("\n❌ 診断で重大な問題が見つかりました")
        sys.exit(1)
    elif warnings:
        print("\n⚠️ 診断で警告が見つかりましたが、継続可能です")
        sys.exit(0)
    else:
        print("\n✅ 診断完了 - すべて正常です")
        sys.exit(0)


def _perform_platform_specific_diagnostics(platform_info):
    """プラットフォーム固有の詳細診断を実行"""
    import os
    import subprocess

    if platform_info.name == "windows":
        print("  Windows固有診断:")

        # PowerShellの実行ポリシーをチェック（precommit環境を考慮）
        try:
            # precommit環境では実行ポリシーチェックをスキップ
            if os.environ.get("PRE_COMMIT") == "1":
                print("    ℹ️ precommit環境のため、PowerShell実行ポリシーチェックをスキップ")
            else:
                result = subprocess.run(
                    ["powershell", "-Command", "Get-ExecutionPolicy"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    policy = result.stdout.strip()
                    print(f"    PowerShell実行ポリシー: {policy}")
                    if policy in ["Restricted", "AllSigned"]:
                        print("    ⚠️ 実行ポリシーが制限的です")
                else:
                    print(f"    ❌ PowerShell実行ポリシーチェック失敗: {result.stderr}")
        except Exception as e:
            print(f"    ❌ PowerShell実行ポリシーチェックエラー: {e}")

        # PATH内のuv関連ディレクトリをチェック
        path_env = os.environ.get("PATH", "")
        uv_paths = [p for p in path_env.split(os.pathsep) if "uv" in p.lower()]
        if uv_paths:
            print(f"    UV関連PATH: {uv_paths}")
        else:
            print("    ⚠️ UV関連のPATHが見つかりません")

    elif platform_info.name == "macos":
        print("  macOS固有診断:")

        # Homebrewの状態をチェック
        path_env = os.environ.get("PATH", "")
        homebrew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]

        for hb_path in homebrew_paths:
            if hb_path in path_env:
                print(f"    ✅ {hb_path} がPATHに含まれています")
            else:
                print(f"    ⚠️ {hb_path} がPATHに含まれていません")

        # シェル情報をチェック
        shell = os.environ.get("SHELL", "")
        print(f"    現在のシェル: {shell}")

        if "zsh" not in shell:
            print("    ⚠️ デフォルトシェルがzshではありません")

    elif platform_info.name == "linux":
        print("  Linux固有診断:")

        # 一般的なLinuxパスをチェック
        path_env = os.environ.get("PATH", "")
        common_paths = ["/usr/bin", "/usr/local/bin", "/bin", "/snap/bin"]

        for common_path in common_paths:
            if common_path in path_env:
                print(f"    ✅ {common_path} がPATHに含まれています")
            else:
                print(f"    ⚠️ {common_path} がPATHに含まれていません")

        # snapdの状態をチェック
        if os.path.exists("/var/lib/snapd"):
            print("    ✅ snapdが利用可能です")
        else:
            print("    ⚠️ snapdが利用できない可能性があります")

    elif platform_info.name == "wsl":
        print("  WSL固有診断:")

        # WSL環境の確認
        try:
            with open("/proc/version", encoding="utf-8") as f:
                version_info = f.read()
                if "microsoft" in version_info.lower() or "wsl" in version_info.lower():
                    print("    ✅ WSL環境が確認されました")
                    print(f"    バージョン情報: {version_info.strip()[:100]}...")
        except Exception as e:
            print(f"    ❌ WSL環境確認エラー: {e}")

        # Windows側のパスが混在していないかチェック
        path_env = os.environ.get("PATH", "")
        windows_paths = [p for p in path_env.split(os.pathsep) if "/mnt/c/" in p]
        if windows_paths:
            print(f"    Windows PATH検出: {len(windows_paths)}個のエントリ")
        else:
            print("    ⚠️ Windows PATHが検出されませんでした")


if __name__ == "__main__":
    main()

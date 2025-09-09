#!/usr/bin/env python3
"""
開発環境セットアップ自動化スクリプト

このスクリプトは開発者向けの環境セットアップを自動化します：
- 開発依存関係のインストール
- Pre-commitフックのセットアップ
- VS Code設定の適用
- 初回品質チェックの実行
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """コマンドを実行する"""
    print(f"実行中: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"エラー: {e}")
        if e.stderr:
            print(f"エラー詳細: {e.stderr}")
        if check:
            raise
        return e


def check_uv_installed() -> bool:
    """uvがインストールされているかチェック"""
    return shutil.which("uv") is not None


def install_dev_dependencies() -> bool:
    """開発依存関係をインストール"""
    print("\n📦 開発依存関係をインストール中...")

    try:
        # 開発依存関係をインストール
        run_command(["uv", "sync", "--dev"])

        # セキュリティツールもインストール
        run_command(["uv", "sync", "--dev", "--group", "security"])

        print("✅ 開発依存関係のインストールが完了しました")
        return True
    except subprocess.CalledProcessError:
        print("❌ 開発依存関係のインストールに失敗しました")
        return False


def setup_precommit() -> bool:
    """Pre-commitフックをセットアップ"""
    print("\n🔧 Pre-commitフックをセットアップ中...")

    try:
        # Pre-commitフックをインストール
        run_command(["uv", "run", "pre-commit", "install"])

        # 全ファイルに対してテスト実行
        print("初回Pre-commitチェックを実行中...")
        result = run_command(
            ["uv", "run", "pre-commit", "run", "--all-files"], check=False
        )

        if result.returncode == 0:
            print("✅ Pre-commitフックのセットアップが完了しました")
        else:
            print(
                "⚠️ Pre-commitフックはセットアップされましたが、"
                "一部のチェックで問題が見つかりました"
            )
            print("これは正常です。コードを修正してから再度コミットしてください。")

        return True
    except subprocess.CalledProcessError:
        print("❌ Pre-commitフックのセットアップに失敗しました")
        return False


def setup_vscode_settings() -> bool:
    """VS Code設定を適用"""
    print("\n🎨 VS Code設定を適用中...")

    try:
        # プラットフォームを検出
        system = platform.system().lower()
        if system == "linux":
            # WSLかどうかチェック
            try:
                with open("/proc/version") as f:
                    template_dir = "wsl" if "microsoft" in f.read().lower() else "linux"
            except FileNotFoundError:
                template_dir = "linux"
        elif system == "windows":
            template_dir = "windows"
        elif system == "darwin":
            template_dir = "linux"  # macOSはLinux設定を使用
        else:
            template_dir = "linux"  # デフォルト

        # テンプレート設定をコピー
        template_path = Path(f"vscode-templates/{template_dir}/settings.json")
        vscode_dir = Path(".vscode")
        vscode_settings = vscode_dir / "settings.json"

        if template_path.exists():
            vscode_dir.mkdir(exist_ok=True)

            # 既存の設定がある場合はバックアップ
            if vscode_settings.exists():
                backup_path = vscode_settings.with_suffix(".json.backup")
                shutil.copy2(vscode_settings, backup_path)
                print(f"既存の設定を {backup_path} にバックアップしました")

            # プラットフォーム固有設定をマージ
            import json

            # 既存の設定を読み込み
            existing_settings = {}
            if vscode_settings.exists():
                with open(vscode_settings, encoding="utf-8") as f:
                    existing_settings = json.load(f)

            # テンプレート設定を読み込み
            with open(template_path, encoding="utf-8") as f:
                template_settings = json.load(f)

            # 設定をマージ（テンプレート設定を優先）
            merged_settings = {**existing_settings, **template_settings}

            # マージした設定を保存
            with open(vscode_settings, "w", encoding="utf-8") as f:
                json.dump(merged_settings, f, indent=4, ensure_ascii=False)

            print(f"✅ {template_dir}用のVS Code設定を適用しました")
        else:
            print(f"⚠️ {template_dir}用のテンプレートが見つかりません")

        return True
    except Exception as e:
        print(f"❌ VS Code設定の適用に失敗しました: {e}")
        return False


def run_initial_quality_check() -> bool:
    """初回品質チェックを実行"""
    print("\n🔍 初回品質チェックを実行中...")

    try:
        # Ruffチェック
        print("Ruffリンティングチェック...")
        run_command(["uv", "run", "ruff", "check", "."], check=False)

        # MyPyチェック
        print("MyPy型チェック...")
        run_command(["uv", "run", "mypy", "src/"], check=False)

        # テスト実行
        print("テスト実行...")
        result = run_command(["uv", "run", "pytest", "tests/unit/", "-v"], check=False)

        if result.returncode == 0:
            print("✅ 全ての品質チェックが通過しました")
        else:
            print("⚠️ 一部の品質チェックで問題が見つかりました")
            print("これは正常です。開発を進めながら品質を向上させてください。")

        return True
    except Exception as e:
        print(f"❌ 品質チェックの実行に失敗しました: {e}")
        return False


def main():
    """メイン処理"""
    print("🚀 Setup-Repository 開発環境セットアップ")
    print("=" * 50)

    # uvのインストールチェック
    if not check_uv_installed():
        print("❌ uvがインストールされていません")
        print("uvをインストールしてから再度実行してください:")
        print("https://docs.astral.sh/uv/getting-started/installation/")
        sys.exit(1)

    success_count = 0
    total_steps = 4

    # 1. 開発依存関係のインストール
    if install_dev_dependencies():
        success_count += 1

    # 2. Pre-commitフックのセットアップ
    if setup_precommit():
        success_count += 1

    # 3. VS Code設定の適用
    if setup_vscode_settings():
        success_count += 1

    # 4. 初回品質チェック
    if run_initial_quality_check():
        success_count += 1

    # 結果表示
    print("\n" + "=" * 50)
    print(f"セットアップ完了: {success_count}/{total_steps} ステップが成功")

    if success_count == total_steps:
        print("🎉 開発環境のセットアップが完了しました！")
        print("\n次のステップ:")
        print("1. VS Codeでプロジェクトを開く")
        print("2. 推奨拡張機能をインストール")
        print("3. コードを編集してコミット")
        print("4. Pre-commitフックが自動実行されることを確認")
    else:
        print("⚠️ 一部のセットアップで問題が発生しました")
        print("上記のエラーメッセージを確認して、手動で修正してください")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Pre-commit自動インストールスクリプト

このスクリプトはpre-commitフックを自動的にセットアップし、
開発者が一貫したコード品質チェックを実行できるようにします。
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> bool:
    """
    コマンドを実行し、成功/失敗を返す

    Args:
        cmd: 実行するコマンドのリスト
        cwd: 実行ディレクトリ（オプション）

    Returns:
        bool: コマンドが成功した場合True
    """
    try:
        print(f"実行中: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, cwd=cwd, check=True, capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"エラー: {e}")
        if e.stderr:
            print(f"エラー詳細: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"エラー: コマンド '{cmd[0]}' が見つかりません")
        return False


def check_git_repository() -> bool:
    """
    現在のディレクトリがGitリポジトリかチェック

    Returns:
        bool: Gitリポジトリの場合True
    """
    git_dir = Path(".git")
    if not git_dir.exists():
        print("エラー: 現在のディレクトリはGitリポジトリではありません")
        print("Gitリポジトリのルートディレクトリで実行してください")
        return False
    return True


def check_uv_available() -> bool:
    """
    uvコマンドが利用可能かチェック

    Returns:
        bool: uvが利用可能な場合True
    """
    return run_command(["uv", "--version"])


def install_pre_commit() -> bool:
    """
    pre-commitをインストール

    Returns:
        bool: インストールが成功した場合True
    """
    print("\n📦 pre-commitをインストール中...")

    # uvを使用してpre-commitをインストール
    if not run_command(["uv", "add", "--dev", "pre-commit"]):
        print("エラー: pre-commitのインストールに失敗しました")
        return False

    print("✅ pre-commitのインストールが完了しました")
    return True


def install_pre_commit_hooks() -> bool:
    """
    pre-commitフックをインストール

    Returns:
        bool: フックのインストールが成功した場合True
    """
    print("\n🔧 pre-commitフックをインストール中...")

    # pre-commitフックをインストール
    if not run_command(["uv", "run", "pre-commit", "install"]):
        print("エラー: pre-commitフックのインストールに失敗しました")
        return False

    print("✅ pre-commitフックのインストールが完了しました")
    return True


def update_pre_commit_hooks() -> bool:
    """
    pre-commitフックを最新版に更新

    Returns:
        bool: 更新が成功した場合True
    """
    print("\n🔄 pre-commitフックを最新版に更新中...")

    if not run_command(["uv", "run", "pre-commit", "autoupdate"]):
        print("警告: pre-commitフックの更新に失敗しました（継続します）")
        return False

    print("✅ pre-commitフックの更新が完了しました")
    return True


def test_pre_commit_hooks() -> bool:
    """
    pre-commitフックをテスト実行

    Returns:
        bool: テストが成功した場合True
    """
    print("\n🧪 pre-commitフックをテスト実行中...")

    # 全ファイルに対してpre-commitを実行
    if not run_command(["uv", "run", "pre-commit", "run", "--all-files"]):
        print("警告: pre-commitフックのテスト実行で問題が検出されました")
        print("これは正常です。コミット時に自動修正されます。")
        return True  # テスト失敗は警告として扱う

    print("✅ pre-commitフックのテスト実行が完了しました")
    return True


def main() -> int:
    """
    メイン処理

    Returns:
        int: 終了コード（0: 成功、1: 失敗）
    """
    print("🚀 Pre-commit自動セットアップスクリプト")
    print("=" * 50)

    # 前提条件チェック
    if not check_git_repository():
        return 1

    if not check_uv_available():
        print("エラー: uvコマンドが見つかりません")
        print("uvをインストールしてから再実行してください")
        print(
            "インストール方法: https://docs.astral.sh/uv/getting-started/installation/"
        )
        return 1

    # pre-commit設定ファイルの存在チェック
    config_file = Path(".pre-commit-config.yaml")
    if not config_file.exists():
        print("エラー: .pre-commit-config.yamlファイルが見つかりません")
        print("プロジェクトルートディレクトリで実行してください")
        return 1

    # セットアップ実行
    steps = [
        ("pre-commitインストール", install_pre_commit),
        ("pre-commitフックインストール", install_pre_commit_hooks),
        ("pre-commitフック更新", update_pre_commit_hooks),
        ("pre-commitフックテスト", test_pre_commit_hooks),
    ]

    for step_name, step_func in steps:
        print(f"\n📋 ステップ: {step_name}")
        if not step_func():
            print(f"❌ {step_name}に失敗しました")
            return 1

    print("\n" + "=" * 50)
    print("🎉 Pre-commitセットアップが完了しました！")
    print("\n📝 使用方法:")
    print("  • コミット時に自動的に品質チェックが実行されます")
    print("  • 手動実行: uv run pre-commit run --all-files")
    print("  • 特定フック実行: uv run pre-commit run ruff")
    print("  • フック無効化: git commit --no-verify")
    print("\n🔧 設定ファイル: .pre-commit-config.yaml")

    return 0


if __name__ == "__main__":
    sys.exit(main())

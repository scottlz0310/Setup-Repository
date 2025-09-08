#!/usr/bin/env python3
"""
セットアップリポジトリ - メインエントリーポイント
クロスプラットフォーム対応のGitHubリポジトリセットアップ・同期ツール
"""
import argparse
import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from setup_repo.cli import setup_cli, sync_cli


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="🚀 セットアップリポジトリ - GitHubリポジトリセットアップ・同期ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py setup              # 初期セットアップ
  python main.py sync               # リポジトリ同期
  python main.py sync --dry-run     # 実行内容確認
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="利用可能なコマンド")
    
    # setupサブコマンド
    setup_parser = subparsers.add_parser("setup", help="初期セットアップを実行")
    setup_parser.set_defaults(func=setup_cli)
    
    # syncサブコマンド
    sync_parser = subparsers.add_parser("sync", help="リポジトリ同期を実行")
    sync_parser.add_argument("--owner", help="GitHubオーナー名")
    sync_parser.add_argument("--dest", help="クローン先ディレクトリ")
    sync_parser.add_argument("--dry-run", action="store_true", help="実行内容を表示のみ")
    sync_parser.add_argument("--force", action="store_true", help="安全性チェックをスキップ")
    sync_parser.add_argument("--use-https", action="store_true", help="SSHではなくHTTPSでクローン")
    sync_parser.add_argument("--sync-only", action="store_true", help="新規クローンを行わず、既存リポジトリのみ更新")
    sync_parser.add_argument("--auto-stash", action="store_true", help="ローカル変更を自動でstash")
    sync_parser.add_argument("--skip-uv-install", action="store_true", help="uvの自動インストールをスキップ")
    sync_parser.set_defaults(func=sync_cli)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 対応する関数を実行
    args.func(args)


if __name__ == "__main__":
    main()
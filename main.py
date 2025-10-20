#!/usr/bin/env python3
"""
セットアップリポジトリ - メインエントリーポイント
クロスプラットフォーム対応のGitHubリポジトリセットアップ・同期ツール
"""

import argparse
import os
import sys
from pathlib import Path

# Windows環境でのUnicodeEncodeError対策
# pytest実行中は標準出力のdetachをスキップ
if sys.platform == "win32" and os.environ.get("PYTEST_RUNNING") != "1":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from setup_repo.cli import (
    backup_cli,
    cleanup_cli,
    deploy_cli,
    migration_cli,
    monitor_cli,
    quality_cli,
    setup_cli,
    sync_cli,
    template_cli,
    trend_cli,
)


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description=("セットアップリポジトリ - GitHubリポジトリセットアップ・同期ツール"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py setup              # 初期セットアップ
  python main.py sync               # リポジトリ同期
  python main.py sync --dry-run     # 実行内容確認
  python main.py quality            # 品質メトリクス収集
  python main.py trend analyze      # 品質トレンド分析
  python main.py template list      # テンプレート一覧
  python main.py template apply --type gitignore --name python  # gitignoreテンプレート適用
  python main.py backup create      # バックアップ作成
  python main.py backup list        # バックアップ一覧
  python main.py migration check     # マイグレーション必要性チェック
  python main.py migration run       # マイグレーション実行
  python main.py migration rollback  # ロールバック
  python main.py monitor health      # システムヘルスチェック
  python main.py monitor performance # パフォーマンス監視
  python main.py monitor alerts      # アラート確認
  python main.py deploy prepare      # デプロイ準備
  python main.py deploy execute      # デプロイ実行
  python main.py deploy rollback     # ロールバック
  python main.py cleanup list        # リモートブランチ一覧
  python main.py cleanup clean --merged  # マージ済みブランチ削除
  python main.py cleanup clean --stale --days 90  # 90日以上更新されていないブランチ削除
        """,
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
    sync_parser.add_argument(
        "--sync-only",
        action="store_true",
        help="新規クローンを行わず、既存リポジトリのみ更新",
    )
    sync_parser.add_argument("--auto-stash", action="store_true", help="ローカル変更を自動でstash")
    sync_parser.add_argument("--skip-uv-install", action="store_true", help="uvの自動インストールをスキップ")
    sync_parser.set_defaults(func=sync_cli)

    # qualityサブコマンド
    quality_parser = subparsers.add_parser("quality", help="品質メトリクス収集を実行")
    quality_parser.add_argument(
        "--project-root",
        help="プロジェクトルートディレクトリ（デフォルト: カレントディレクトリ）",
    )
    quality_parser.add_argument("--output", help="レポート出力ファイル（デフォルト: quality-report.json）")
    quality_parser.add_argument("--save-trend", action="store_true", help="トレンドデータに結果を保存")
    quality_parser.set_defaults(func=quality_cli)

    # trendサブコマンド
    trend_parser = subparsers.add_parser("trend", help="品質トレンド分析を実行")
    trend_parser.add_argument("action", choices=["analyze", "report", "clean"], help="実行するアクション")
    trend_parser.add_argument(
        "--project-root",
        help="プロジェクトルートディレクトリ（デフォルト: カレントディレクトリ）",
    )
    trend_parser.add_argument(
        "--trend-file",
        help="トレンドデータファイル（デフォルト: quality-trends/trend-data.json）",
    )
    trend_parser.add_argument("--days", type=int, default=30, help="分析期間（日数、デフォルト: 30）")
    trend_parser.add_argument(
        "--output",
        help="レポート出力ファイル（デフォルト: quality-trends/trend-report.html）",
    )
    trend_parser.add_argument("--keep-days", type=int, help="保持する日数（cleanアクション用）")
    trend_parser.set_defaults(func=trend_cli)

    # templateサブコマンド
    template_parser = subparsers.add_parser("template", help="テンプレート管理を実行")
    template_parser.add_argument("action", choices=["list", "apply", "create", "remove"], help="実行するアクション")
    template_parser.add_argument("--name", help="テンプレート名")
    template_parser.add_argument("--type", choices=["gitignore", "vscode", "custom"], help="テンプレートタイプ")
    template_parser.add_argument("--source", help="ソースパス（createアクション用）")
    template_parser.add_argument("--target", help="適用先パス（applyアクション用）")
    template_parser.add_argument(
        "--project-root",
        help="プロジェクトルートディレクトリ（デフォルト: カレントディレクトリ）",
    )
    template_parser.set_defaults(func=template_cli)

    # backupサブコマンド
    backup_parser = subparsers.add_parser("backup", help="バックアップ管理を実行")
    backup_parser.add_argument("action", choices=["create", "list", "restore", "remove"], help="実行するアクション")
    backup_parser.add_argument("--name", help="バックアップ名")
    backup_parser.add_argument("--target", help="復元先パス（restoreアクション用）")
    backup_parser.add_argument(
        "--project-root",
        help="プロジェクトルートディレクトリ（デフォルト: カレントディレクトリ）",
    )
    backup_parser.set_defaults(func=backup_cli)

    # migrationサブコマンド
    migration_parser = subparsers.add_parser("migration", help="マイグレーション管理を実行")
    migration_parser.add_argument("action", choices=["check", "run", "rollback"], help="実行するアクション")
    migration_parser.add_argument("--backup-name", help="ロールバック用バックアップ名")
    migration_parser.add_argument("--no-backup", action="store_true", help="バックアップを作成しない")
    migration_parser.add_argument(
        "--project-root",
        help="プロジェクトルートディレクトリ（デフォルト: カレントディレクトリ）",
    )
    migration_parser.set_defaults(func=migration_cli)

    # monitorサブコマンド
    monitor_parser = subparsers.add_parser("monitor", help="システム監視・ヘルスチェックを実行")
    monitor_parser.add_argument(
        "action", choices=["health", "performance", "alerts", "dashboard"], help="実行するアクション"
    )
    monitor_parser.add_argument(
        "--project-root",
        help="プロジェクトルートディレクトリ（デフォルト: カレントディレクトリ）",
    )
    monitor_parser.add_argument("--output", help="出力ファイル")
    monitor_parser.add_argument("--watch", action="store_true", help="継続監視モード")
    monitor_parser.add_argument("--interval", type=int, default=60, help="監視間隔（秒、デフォルト: 60）")
    monitor_parser.set_defaults(func=monitor_cli)

    # deployサブコマンド
    deploy_parser = subparsers.add_parser("deploy", help="デプロイメント管理を実行")
    deploy_parser.add_argument("action", choices=["prepare", "execute", "rollback", "list"], help="実行するアクション")
    deploy_parser.add_argument("--environment", help="デプロイ環境（デフォルト: production）")
    deploy_parser.add_argument("--deploy-id", help="ロールバック対象のデプロイID")
    deploy_parser.set_defaults(func=deploy_cli)

    # cleanupサブコマンド
    cleanup_parser = subparsers.add_parser("cleanup", help="リモートブランチクリーンナップを実行")
    cleanup_parser.add_argument("action", choices=["list", "clean"], help="実行するアクション")
    cleanup_parser.add_argument("--repo-path", help="リポジトリパス（デフォルト: カレントディレクトリ）")
    cleanup_parser.add_argument("--merged", action="store_true", help="マージ済みブランチを対象")
    cleanup_parser.add_argument("--stale", action="store_true", help="古いブランチを対象")
    cleanup_parser.add_argument("--base-branch", help="ベースブランチ（デフォルト: origin/main）")
    cleanup_parser.add_argument("--days", type=int, help="古いブランチの日数閾値（デフォルト: 90）")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="実行内容を表示のみ")
    cleanup_parser.add_argument("-y", "--yes", action="store_true", help="確認なしで実行")
    cleanup_parser.set_defaults(func=cleanup_cli)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 対応する関数を実行
    args.func(args)


if __name__ == "__main__":
    main()

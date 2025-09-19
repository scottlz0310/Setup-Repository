"""CLI コマンドハンドラー"""

from pathlib import Path

from .backup_manager import BackupManager
from .config import load_config
from .quality_metrics import QualityMetricsCollector
from .quality_trends import QualityTrendManager
from .security_helpers import safe_path_join
from .setup import run_interactive_setup
from .sync import sync_repositories
from .template_manager import TemplateManager


def setup_cli(args) -> None:
    """初期セットアップコマンド"""
    run_interactive_setup()


def sync_cli(args) -> None:
    """リポジトリ同期コマンド"""
    config = load_config()

    # コマンドライン引数で設定を上書き
    if args.owner:
        config["owner"] = args.owner
    if args.dest:
        config["dest"] = args.dest

    config.update(
        {
            "dry_run": args.dry_run,
            "force": args.force,
            "use_https": args.use_https or config.get("use_https", False),
            "sync_only": args.sync_only or config.get("sync_only", False),
            "auto_stash": args.auto_stash or config.get("auto_stash", False),
            "skip_uv_install": args.skip_uv_install or config.get("skip_uv_install", False),
        }
    )

    # リポジトリ同期実行
    sync_repositories(config)


def quality_cli(args) -> None:
    """品質メトリクス収集コマンド"""
    if args.project_root:
        try:
            project_root = safe_path_join(Path.cwd(), args.project_root)
        except ValueError as e:
            raise ValueError(f"不正なプロジェクトルートパス: {e}") from e
    else:
        project_root = Path.cwd()
    collector = QualityMetricsCollector(project_root)

    # メトリクス収集
    metrics = collector.collect_all_metrics()

    # レポート保存
    output_file = None
    if args.output:
        try:
            output_file = safe_path_join(project_root, args.output)
        except ValueError as e:
            raise ValueError(f"不正な出力ファイルパス: {e}") from e
    report_file = collector.save_metrics_report(metrics, output_file)

    print("\n品質メトリクス収集完了:")
    print(f"  品質スコア: {metrics.get_quality_score():.1f}/100")
    print(f"  テストカバレッジ: {metrics.test_coverage:.1f}%")
    print(f"  Ruffエラー: {metrics.ruff_issues}件")
    print(f"  MyPyエラー: {metrics.mypy_errors}件")
    print(f"  セキュリティ脆弱性: {metrics.security_vulnerabilities}件")
    print(f"  レポートファイル: {report_file}")

    # トレンドデータに追加
    if args.save_trend:
        output_dir = safe_path_join(project_root, "output/quality-trends")
        output_dir.mkdir(parents=True, exist_ok=True)
        trend_file = safe_path_join(output_dir, "trend-data.json")
        trend_manager = QualityTrendManager(trend_file)
        trend_manager.add_data_point(metrics)
        print("  トレンドデータを更新しました")

    # 品質基準チェック
    if not metrics.is_passing():
        print("\n⚠️  品質基準を満たしていません")
        exit(1)
    else:
        print("\n✅ 品質基準を満たしています")


def trend_cli(args) -> None:
    """品質トレンド分析コマンド"""
    if args.project_root:
        try:
            project_root = safe_path_join(Path.cwd(), args.project_root)
        except ValueError as e:
            raise ValueError(f"不正なプロジェクトルートパス: {e}") from e
    else:
        project_root = Path.cwd()

    if args.trend_file:
        try:
            trend_file = safe_path_join(project_root, args.trend_file)
        except ValueError as e:
            raise ValueError(f"不正なトレンドファイルパス: {e}") from e
    else:
        output_dir = safe_path_join(project_root, "output/quality-trends")
        output_dir.mkdir(parents=True, exist_ok=True)
        trend_file = safe_path_join(output_dir, "trend-data.json")

    trend_manager = QualityTrendManager(trend_file)

    if args.action == "analyze":
        # トレンド分析
        analysis = trend_manager.analyze_trend(args.days)

        print("\n" + "=" * 60)
        print("📈 品質トレンド分析")
        print("=" * 60)
        print(f"分析期間: {analysis.period_days}日")
        print(f"データポイント数: {analysis.data_points}件")
        print(f"平均品質スコア: {analysis.average_quality_score:.1f}%")
        print(f"平均カバレッジ: {analysis.average_coverage:.1f}%")
        print(f"品質スコアトレンド: {analysis.quality_score_trend}")
        print(f"カバレッジトレンド: {analysis.coverage_trend}")

        if analysis.recent_issues:
            print("\n🚨 最近の問題:")
            for issue in analysis.recent_issues:
                print(f"  - {issue}")

        print("\n💡 推奨事項:")
        for recommendation in analysis.recommendations:
            print(f"  - {recommendation}")

    elif args.action == "report":
        # HTMLレポート生成
        if args.output:
            try:
                output_file = safe_path_join(project_root, args.output)
            except ValueError as e:
                raise ValueError(f"不正な出力ファイルパス: {e}") from e
        else:
            output_dir = safe_path_join(project_root, "output")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = safe_path_join(output_dir, "trend-report.html")
        report_file = trend_manager.generate_html_report(output_file)
        print(f"HTMLレポートを生成しました: {report_file}")

    elif args.action == "clean":
        # 古いデータの削除
        data_points = trend_manager.load_trend_data()
        if args.keep_days:
            from datetime import datetime, timedelta

            cutoff_date = datetime.now() - timedelta(days=args.keep_days)
            filtered_points = [
                point
                for point in data_points
                if datetime.fromisoformat(point.timestamp.replace("Z", "+00:00")) >= cutoff_date
            ]
            trend_manager.save_trend_data(filtered_points)
            removed_count = len(data_points) - len(filtered_points)
            print(f"{removed_count}件の古いデータを削除しました")
        else:
            print("--keep-daysオプションを指定してください")


def template_cli(args) -> None:
    """テンプレート管理コマンド"""
    if args.project_root:
        try:
            project_root = safe_path_join(Path.cwd(), args.project_root)
        except ValueError as e:
            raise ValueError(f"不正なプロジェクトルートパス: {e}") from e
    else:
        project_root = Path.cwd()

    if args.action == "list":
        manager = TemplateManager(project_root)
        # テンプレート一覧表示
        templates = manager.list_templates()

        print("\n利用可能なテンプレート:")
        print("=" * 40)

        if templates["gitignore"]:
            print("\n📄 Gitignoreテンプレート:")
            for template in templates["gitignore"]:
                print(f"  - {template}")

        if templates["vscode"]:
            print("\n🔧 VS Codeテンプレート:")
            for template in templates["vscode"]:
                print(f"  - {template}")

        if templates["custom"]:
            print("\n🎨 カスタムテンプレート:")
            for template in templates["custom"]:
                print(f"  - {template}")

        if not any(templates.values()):
            print("テンプレートが見つかりません")

    elif args.action == "apply":
        # テンプレート適用
        if not args.name:
            print("エラー: テンプレート名を指定してください")
            return

        target_path = Path.cwd()
        if args.target:
            try:
                target_path = safe_path_join(Path.cwd(), args.target)
            except ValueError as e:
                raise ValueError(f"不正なターゲットパス: {e}") from e

        # project_rootとtarget_pathを分離して使用
        manager = TemplateManager(project_root)

        try:
            if args.type == "gitignore":
                result_path = manager.apply_gitignore_template(args.name, target_path)
                print(f"✅ Gitignoreテンプレート '{args.name}' を適用しました: {result_path}")
            elif args.type == "vscode":
                result_path = manager.apply_vscode_template(args.name, target_path)
                print(f"✅ VS Codeテンプレート '{args.name}' を適用しました: {result_path}")
            elif args.type == "custom":
                result_path = manager.apply_custom_template(args.name, target_path)
                print(f"✅ カスタムテンプレート '{args.name}' を適用しました: {result_path}")
            else:
                print("エラー: テンプレートタイプを指定してください (gitignore/vscode/custom)")
        except FileNotFoundError as e:
            print(f"エラー: {e}")
        except Exception as e:
            print(f"エラー: テンプレート適用に失敗しました: {e}")

    elif args.action == "create":
        # カスタムテンプレート作成
        if not args.name or not args.source:
            print("エラー: テンプレート名とソースパスを指定してください")
            return

        manager = TemplateManager(project_root)
        try:
            source_path = safe_path_join(project_root, args.source)
            result_path = manager.create_custom_template(args.name, source_path)
            print(f"✅ カスタムテンプレート '{args.name}' を作成しました: {result_path}")
        except (FileNotFoundError, FileExistsError) as e:
            print(f"エラー: {e}")
        except Exception as e:
            print(f"エラー: テンプレート作成に失敗しました: {e}")

    elif args.action == "remove":
        # カスタムテンプレート削除
        if not args.name:
            print("エラー: テンプレート名を指定してください")
            return

        manager = TemplateManager(project_root)
        if manager.remove_template(args.name):
            print(f"✅ カスタムテンプレート '{args.name}' を削除しました")
        else:
            print(f"エラー: テンプレート '{args.name}' が見つかりません")

    else:
        print("エラー: 不正なアクション。list/apply/create/remove のいずれかを指定してください")


def backup_cli(args) -> None:
    """バックアップ管理コマンド"""
    if args.project_root:
        try:
            project_root = safe_path_join(Path.cwd(), args.project_root)
        except ValueError as e:
            raise ValueError(f"不正なプロジェクトルートパス: {e}") from e
    else:
        project_root = Path.cwd()

    manager = BackupManager(project_root)

    if args.action == "create":
        # バックアップ作成
        try:
            backup_path = manager.create_backup(args.name)
            print(f"✅ バックアップを作成しました: {backup_path}")
        except Exception as e:
            print(f"エラー: バックアップ作成に失敗しました: {e}")

    elif args.action == "list":
        # バックアップ一覧
        backups = manager.list_backups()

        if not backups:
            print("バックアップが見つかりません")
            return

        print("\n利用可能なバックアップ:")
        print("=" * 60)

        for backup in backups:
            size_mb = backup["file_size"] / (1024 * 1024)
            created_at = backup["created_at"][:19].replace("T", " ")
            print(f"\n💾 {backup['name']}")
            print(f"  作成日時: {created_at}")
            print(f"  ファイルサイズ: {size_mb:.1f} MB")

            if backup.get("targets"):
                print("  バックアップ対象:")
                for target in backup["targets"]:
                    target_size = target["size"] / 1024 if target["size"] > 0 else 0
                    print(f"    - {target['path']} ({target['type']}, {target_size:.1f} KB)")

    elif args.action == "restore":
        # バックアップ復元
        if not args.name:
            print("エラー: バックアップ名を指定してください")
            return

        target_path = None
        if args.target:
            try:
                target_path = safe_path_join(Path.cwd(), args.target)
            except ValueError as e:
                raise ValueError(f"不正なターゲットパス: {e}") from e

        try:
            success = manager.restore_backup(args.name, target_path)
            if success:
                restore_path = target_path or project_root
                print(f"✅ バックアップ '{args.name}' を復元しました: {restore_path}")
                print("⚠️  既存ファイルは .restore_backup ディレクトリにバックアップされました")
        except (FileNotFoundError, RuntimeError) as e:
            print(f"エラー: {e}")

    elif args.action == "remove":
        # バックアップ削除
        if not args.name:
            print("エラー: バックアップ名を指定してください")
            return

        if manager.remove_backup(args.name):
            print(f"✅ バックアップ '{args.name}' を削除しました")
        else:
            print(f"エラー: バックアップ '{args.name}' が見つかりません")

    else:
        print("エラー: 不正なアクション。create/list/restore/remove のいずれかを指定してください")

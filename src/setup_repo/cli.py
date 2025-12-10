"""CLI コマンドハンドラー"""

import argparse
import builtins
import os
import sys
from pathlib import Path

from .backup_manager import BackupManager
from .branch_cleanup import BranchCleanup
from .config import load_config
from .deploy_manager import DeployManager
from .migration_manager import MigrationManager
from .monitor_manager import MonitorManager
from .quality_metrics import QualityMetricsCollector
from .quality_trends import QualityTrendManager
from .security_helpers import safe_path_join
from .setup import run_interactive_setup
from .sync import sync_repositories
from .template_manager import TemplateManager

_original_print = builtins.print
builtins.print = lambda *args, **kwargs: _original_print(*args, **{**kwargs, "flush": True})

# Windows環境でのUnicodeエンコーディング問題を修正
# pytest実行中は標準出力のdetachをスキップ
if os.name == "nt" and os.environ.get("PYTEST_RUNNING") != "1":
    import codecs

    # 既にdetachされている場合はスキップ
    try:
        if hasattr(sys.stdout, "detach"):
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass  # 既にdetachされているか、利用できない場合はスキップ

    try:
        if hasattr(sys.stderr, "detach"):
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass  # 既にdetachされているか、利用できない場合はスキップ

# 出力バッファリング無効化（全プラットフォーム）
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except (AttributeError, OSError):
    pass  # Python 3.7以前またはreconfigureが利用できない場合はスキップ


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
    print(f"  Pyrightエラー: {metrics.pyright_errors}件")
    # 互換性のため mypy_errors も表示
    print(f"  MyPyエラー (互換): {metrics.mypy_errors}件")
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


def monitor_cli(args) -> None:
    """監視・ヘルスチェックコマンド"""
    if args.project_root:
        try:
            project_root = safe_path_join(Path.cwd(), args.project_root)
        except ValueError as e:
            raise ValueError(f"不正なプロジェクトルートパス: {e}") from e
    else:
        project_root = Path.cwd()

    manager = MonitorManager(project_root)

    if args.action == "health":
        # ヘルスチェック実行
        health_data = manager.run_health_check()

        print("\n" + "=" * 60)
        print("🏥 システムヘルスチェック")
        print("=" * 60)
        print(f"全体ステータス: {health_data['overall_status'].upper()}")
        print(f"チェック時刻: {health_data['timestamp'][:19].replace('T', ' ')}")

        # システム情報
        system = health_data["system"]
        print("\n💻 システム情報:")
        print(f"  プラットフォーム: {system['platform']} {system['architecture']}")
        print(f"  Python: {system['python_version'].split()[0]}")

        # リソース使用状況
        resources = health_data["resources"]
        print("\n📊 リソース使用状況:")
        print(f"  CPU使用率: {resources['cpu_usage_percent']:.1f}%")
        print(
            f"  メモリ使用率: {resources['memory_usage_percent']:.1f}% "
            f"({resources['memory_used_gb']:.1f}GB / {resources['memory_total_gb']:.1f}GB)"
        )
        print(
            f"  ディスク使用率: {resources['disk_usage_percent']:.1f}% "
            f"({resources['disk_used_gb']:.1f}GB / {resources['disk_total_gb']:.1f}GB)"
        )

        # 依存関係
        deps = health_data["dependencies"]
        print("\n🔧 依存関係:")
        print(f"  uv: {'✅' if deps['uv_available'] else '❌'}")
        print(f"  Git: {'✅' if deps['git_available'] else '❌'}")
        print(f"  Python (>=3.9): {'✅' if deps['python_version_supported'] else '❌'}")

        for tool, info in deps["required_tools"].items():
            status = "✅" if info["available"] else "❌"
            version = f" ({info['version']})" if info["version"] else ""
            print(f"  {tool}: {status}{version}")

        # プロジェクト状態
        project = health_data["project"]
        print("\n📁 プロジェクト状態:")
        print(f"  設定ファイル: {'✅' if project['config_exists'] else '❌'}")
        print(f"  pyproject.toml: {'✅' if project['pyproject_exists'] else '❌'}")
        print(f"  Gitリポジトリ: {'✅' if project['git_repo'] else '❌'}")

        if project["quality_metrics"]:
            qm = project["quality_metrics"]
            print(f"  品質スコア: {qm['quality_score']:.1f}/100")
            print(f"  テストカバレッジ: {qm['test_coverage']:.1f}%")
            print(f"  Ruffエラー: {qm['ruff_issues']}件")
            print(f"  MyPyエラー: {qm['mypy_errors']}件")
            print(f"  セキュリティ脆弱性: {qm['security_vulnerabilities']}件")

        # 問題と推奨事項
        if health_data["issues"]:
            print("\n🚨 検出された問題:")
            for issue in health_data["issues"]:
                print(f"  - {issue}")

        if health_data["recommendations"]:
            print("\n💡 推奨事項:")
            for rec in health_data["recommendations"]:
                print(f"  - {rec}")

        # 出力ファイル保存
        if args.output:
            try:
                output_dir = safe_path_join(project_root, "output")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = safe_path_join(output_dir, args.output)
                with open(output_file, "w", encoding="utf-8") as f:
                    import json

                    json.dump(health_data, f, indent=2, ensure_ascii=False)
                print(f"\n📄 ヘルスチェック結果を保存しました: {output_file}")
            except Exception as e:
                print(f"エラー: 出力ファイルの保存に失敗しました: {e}")

    elif args.action == "performance":
        # パフォーマンス監視
        perf_data = manager.run_performance_monitoring()

        print("\n" + "=" * 60)
        print("⚡ パフォーマンス監視")
        print("=" * 60)
        print(f"監視時刻: {perf_data['timestamp'][:19].replace('T', ' ')}")

        # システムパフォーマンス
        sys_perf = perf_data["system_performance"]
        print("\n💻 システムパフォーマンス:")
        print(f"  CPUコア数: {sys_perf['cpu_count']}")
        print(f"  CPU使用率: {sys_perf['cpu_usage']}")
        print(f"  メモリ使用率: {sys_perf['memory']['percent']:.1f}%")
        print(f"  利用可能メモリ: {sys_perf['memory']['available'] / (1024**3):.1f}GB")

        # プロジェクトパフォーマンス
        proj_perf = perf_data["project_performance"]
        print("\n📁 プロジェクトメトリクス:")
        print(f"  総ファイル数: {proj_perf['file_count']:,}")
        print(f"  総サイズ: {proj_perf['total_size'] / (1024**2):.1f}MB")
        print(f"  Pythonファイル数: {proj_perf['python_files']:,}")
        print(f"  テストファイル数: {proj_perf['test_files']:,}")

        print("\n📊 パフォーマンスデータを保存しました: output/monitoring/")

    elif args.action == "alerts":
        # アラートチェック
        alerts = manager.run_alert_check()

        print("\n" + "=" * 60)
        print("🚨 アラートチェック")
        print("=" * 60)

        if not alerts:
            print("✅ アクティブなアラートはありません")
        else:
            print(f"⚠️  {len(alerts)}件のアラートが検出されました:\n")
            for alert in alerts:
                severity_icon = {
                    "critical": "🔴",
                    "high": "🟠",
                    "warning": "🟡",
                    "info": "🔵",
                }.get(alert["severity"], "⚪")
                print(f"  {severity_icon} [{alert['severity'].upper()}] {alert['message']}")
                print(f"    タイプ: {alert['type']}, 時刻: {alert['timestamp'][:19].replace('T', ' ')}")

            print("\n📄 アラートデータを保存しました: output/alerts/")

    elif args.action == "dashboard":
        # ダッシュボードデータ生成
        dashboard_data = manager.generate_dashboard_data()

        print("\n" + "=" * 60)
        print("📊 システムダッシュボード")
        print("=" * 60)

        summary = dashboard_data["summary"]
        print(f"全体ステータス: {summary['overall_status'].upper()}")
        print(f"アクティブアラート: {summary['active_alerts']}件")
        print(f"CPU使用率: {summary['cpu_usage']:.1f}%")
        print(f"メモリ使用率: {summary['memory_usage']:.1f}%")
        print(f"ディスク使用率: {summary['disk_usage']:.1f}%")

        # 出力ファイル保存
        output_dir = safe_path_join(project_root, "output")
        output_dir.mkdir(parents=True, exist_ok=True)

        if args.output:
            try:
                output_file = safe_path_join(output_dir, args.output)
            except ValueError as e:
                raise ValueError(f"不正な出力ファイルパス: {e}") from e
        else:
            output_file = safe_path_join(output_dir, "dashboard.json")

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                import json

                json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
            print(f"\n📄 ダッシュボードデータを保存しました: {output_file}")
        except Exception as e:
            print(f"エラー: 出力ファイルの保存に失敗しました: {e}")

    else:
        print("エラー: 不正なアクション。health/performance/alerts/dashboard のいずれかを指定してください")


def migration_cli(args) -> None:
    """マイグレーション管理コマンド"""
    if args.project_root:
        try:
            project_root = safe_path_join(Path.cwd(), args.project_root)
        except ValueError as e:
            raise ValueError(f"不正なプロジェクトルートパス: {e}") from e
    else:
        project_root = Path.cwd()

    manager = MigrationManager(project_root)

    if args.action == "check":
        # マイグレーション必要性チェック
        result = manager.check_migration_needed()

        print("\n" + "=" * 60)
        print("🔄 マイグレーションチェック")
        print("=" * 60)
        print(f"現在のバージョン: {result['current_version']}")
        print(f"ターゲットバージョン: {result['target_version']}")
        print(f"マイグレーション必要: {'はい' if result['migration_needed'] else 'いいえ'}")

        if result["changes"]:
            print("\n📋 検出された変更:")
            for change in result["changes"]:
                print(f"  - {change['description']}")
                print(f"    タイプ: {change['type']}")
        else:
            print("\n✅ 変更は検出されませんでした")

    elif args.action == "run":
        # マイグレーション実行
        print("\n🔄 マイグレーションを実行中...")
        result = manager.run_migration(backup=not args.no_backup)

        if result["success"]:
            print(f"✅ {result['message']}")
            if result.get("backup_path"):
                print(f"📦 バックアップ: {result['backup_path']}")

            if result.get("migration_result", {}).get("migrations"):
                print("\n📋 実行されたマイグレーション:")
                for migration in result["migration_result"]["migrations"]:
                    print(f"  - {migration['description']}")
                    if migration.get("backup_file"):
                        print(f"    バックアップ: {migration['backup_file']}")
        else:
            print(f"❌ マイグレーション失敗: {result['error']}")
            if result.get("backup_path"):
                print(f"📦 バックアップから復元可能: {result['backup_path']}")
            exit(1)

    elif args.action == "rollback":
        # マイグレーションロールバック
        print("\n⏪ マイグレーションロールバックを実行中...")
        result = manager.rollback_migration(args.backup_name)

        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ ロールバック失敗: {result['error']}")
            exit(1)

    else:
        print("エラー: 不正なアクション。check/run/rollback のいずれかを指定してください")


def deploy_cli(args) -> None:
    """デプロイメント管理コマンド"""
    config = load_config()
    manager = DeployManager(config)

    if args.action == "prepare":
        # デプロイ準備
        print("\n🚀 デプロイ準備を開始します...")
        if manager.prepare():
            print("✅ デプロイ準備が完了しました")
        else:
            print("❌ デプロイ準備に失敗しました")
            exit(1)

    elif args.action == "execute":
        # デプロイ実行
        environment = args.environment or "production"
        print(f"\n🚀 環境 '{environment}' へのデプロイを開始します...")
        if manager.execute(environment):
            print("✅ デプロイが正常に完了しました")
        else:
            print("❌ デプロイに失敗しました")
            exit(1)

    elif args.action == "rollback":
        # ロールバック実行
        print("\n⏪ ロールバックを開始します...")
        if manager.rollback(args.deploy_id):
            print("✅ ロールバックが正常に完了しました")
        else:
            print("❌ ロールバックに失敗しました")
            exit(1)

    elif args.action == "list":
        # デプロイ履歴一覧
        deployments = manager.list_deployments()

        if not deployments:
            print("デプロイ履歴が見つかりません")
            return

        print("\n📋 デプロイ履歴:")
        print("=" * 80)

        for deployment in reversed(deployments[-10:]):  # 最新10件
            status_icon = "✅" if deployment["status"] == "success" else "❌"
            timestamp = deployment["timestamp"][:19].replace("T", " ")
            print(f"\n{status_icon} {deployment['deploy_id']}")
            print(f"  環境: {deployment['environment']}")
            print(f"  ステータス: {deployment['status']}")
            print(f"  時刻: {timestamp}")
            print(f"  コミット: {deployment['commit_hash'][:8]}")
            print(f"  ブランチ: {deployment['branch']}")

            if deployment.get("rollback_target"):
                print(f"  ロールバック対象: {deployment['rollback_target']}")

    else:
        print("エラー: 不正なアクション。prepare/execute/rollback/list のいずれかを指定してください")


def cleanup_cli(args) -> None:
    """ブランチクリーンナップコマンド"""
    if args.repo_path:
        try:
            repo_path = safe_path_join(Path.cwd(), args.repo_path)
        except ValueError as e:
            raise ValueError(f"不正なリポジトリパス: {e}") from e
    else:
        repo_path = Path.cwd()

    if not (repo_path / ".git").exists():
        print("エラー: Gitリポジトリではありません")
        exit(1)

    cleanup = BranchCleanup(repo_path)

    if args.action == "list":
        # ブランチ一覧表示
        if args.merged:
            base_branch = args.base_branch or "origin/main"
            merged_branches = cleanup.list_merged_branches(base_branch)
            print(f"\n📋 マージ済みブランチ ({base_branch}): {len(merged_branches)}件")
            for branch in merged_branches:
                print(f"   - {branch}")
        elif args.stale:
            days = args.days or 90
            stale_branches = cleanup.list_stale_branches(days)
            print(f"\n📋 {days}日以上更新されていないブランチ: {len(stale_branches)}件")
            for stale_branch in stale_branches:
                print(f"   - {stale_branch['name']} (最終更新: {stale_branch['last_commit_date'][:10]})")
        else:
            all_branches = cleanup.list_remote_branches()
            print(f"\n📋 リモートブランチ: {len(all_branches)}件")
            for remote_branch in all_branches:
                print(f"   - {remote_branch['name']} (最終更新: {remote_branch['last_commit_date'][:10]})")

    elif args.action == "clean":
        # ブランチクリーンナップ実行
        result = None
        if args.merged:
            base_branch = args.base_branch or "origin/main"
            print(f"\n🧹 マージ済みブランチをクリーンナップします (ベース: {base_branch})")
            result = cleanup.cleanup_merged_branches(
                base_branch=base_branch, dry_run=args.dry_run, auto_confirm=args.yes
            )
        elif args.stale:
            days = args.days or 90
            print(f"\n🧹 {days}日以上更新されていないブランチをクリーンナップします")
            result = cleanup.cleanup_stale_branches(days=days, dry_run=args.dry_run, auto_confirm=args.yes)
        else:
            print("エラー: --merged または --stale を指定してください")
            exit(1)

        # 結果表示
        if result is not None:
            print("\n" + "=" * 60)
            print("📊 クリーンナップ結果")
            print("=" * 60)
            print(f"削除: {result['deleted']}件")
            print(f"失敗: {result['failed']}件")
            print(f"スキップ: {result['skipped']}件")

            if result["branches"] and not args.dry_run:
                print("\n削除されたブランチ:")
                for branch_name in result["branches"]:
                    print(f"   - {branch_name}")

    else:
        print("エラー: 不正なアクション。list/clean のいずれかを指定してください")


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description=("セットアップリポジトリ - GitHubリポジトリセットアップ・同期ツール"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  setup-repo setup              # 初期セットアップ
  setup-repo sync               # リポジトリ同期
  setup-repo sync --dry-run     # 実行内容確認
  setup-repo quality            # 品質メトリクス収集
  setup-repo trend analyze      # 品質トレンド分析
  setup-repo template list      # テンプレート一覧
  setup-repo backup create      # バックアップ作成
  setup-repo migration check    # マイグレーション必要性チェック
  setup-repo monitor health     # システムヘルスチェック
  setup-repo deploy prepare     # デプロイ準備
  setup-repo cleanup list       # リモートブランチ一覧
  setup-repo cleanup clean --merged  # マージ済みブランチ削除
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

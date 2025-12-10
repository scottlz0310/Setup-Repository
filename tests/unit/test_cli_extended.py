"""
拡張CLIコマンドのテスト（template, backup, monitor）

ルール5章準拠の実際のバグ検出能力を持つテスト
"""

from pathlib import Path
from unittest.mock import Mock, patch

from setup_repo.cli import backup_cli, monitor_cli, template_cli
from tests.multiplatform.helpers import verify_current_platform


class TestTemplateCLI:
    """テンプレートCLI機能のテスト"""

    def test_template_cli_list_action(self):
        """テンプレート一覧表示テスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "list"

        with patch("setup_repo.cli.TemplateManager") as mock_manager:
            mock_instance = Mock()
            mock_instance.list_templates.return_value = {
                "gitignore": ["python", "node"],
                "vscode": ["python-dev"],
                "custom": ["my-template"],
            }
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                template_cli(args)

            mock_instance.list_templates.assert_called_once()

    def test_template_cli_apply_gitignore(self):
        """Gitignoreテンプレート適用テスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "apply"
        args.name = "python"
        args.type = "gitignore"
        args.target = None

        with (
            patch("setup_repo.cli.TemplateManager") as mock_manager,
            patch("setup_repo.cli.safe_path_join") as mock_path_join,
        ):
            mock_path_join.return_value = Path.cwd()
            mock_instance = Mock()
            mock_instance.apply_gitignore_template.return_value = Path(".gitignore")
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                template_cli(args)

            mock_instance.apply_gitignore_template.assert_called_once_with("python", Path.cwd())

    def test_template_cli_apply_missing_name(self):
        """テンプレート名未指定エラーテスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "apply"
        args.name = None
        args.type = "gitignore"
        args.target = None

        with patch("builtins.print") as mock_print:
            template_cli(args)

        mock_print.assert_called_with("エラー: テンプレート名を指定してください")

    def test_template_cli_create_basic(self):
        """カスタムテンプレート作成基本テスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "create"
        args.name = "my-template"
        args.source = "template-source"

        with (
            patch("setup_repo.cli.TemplateManager") as mock_manager,
            patch("setup_repo.cli.safe_path_join") as mock_path_join,
        ):
            mock_path_join.side_effect = [Path.cwd(), Path("template-source")]
            mock_instance = Mock()
            mock_instance.create_custom_template.return_value = Path("custom-templates/my-template")
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                template_cli(args)

            mock_instance.create_custom_template.assert_called_once()

    def test_template_cli_invalid_action(self):
        """不正なアクションエラーテスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "invalid"

        with patch("builtins.print") as mock_print:
            template_cli(args)

        mock_print.assert_called_with("エラー: 不正なアクション。list/apply/create/remove のいずれかを指定してください")


class TestBackupCLI:
    """バックアップCLI機能のテスト"""

    def test_backup_cli_create_action(self):
        """バックアップ作成テスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "create"
        args.name = "test-backup"

        with patch("setup_repo.cli.BackupManager") as mock_manager:
            mock_instance = Mock()
            mock_instance.create_backup.return_value = Path("backups/test-backup.zip")
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                backup_cli(args)

            mock_instance.create_backup.assert_called_once_with("test-backup")

    def test_backup_cli_list_action(self):
        """バックアップ一覧表示テスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "list"

        with patch("setup_repo.cli.BackupManager") as mock_manager:
            mock_instance = Mock()
            mock_instance.list_backups.return_value = [
                {
                    "name": "backup1",
                    "created_at": "2025-01-27T10:00:00Z",
                    "file_size": 1024 * 1024,
                    "targets": [{"path": "config.json", "type": "file", "size": 1024}],
                }
            ]
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                backup_cli(args)

            mock_instance.list_backups.assert_called_once()

    def test_backup_cli_restore_action(self):
        """バックアップ復元テスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "restore"
        args.name = "test-backup"
        args.target = None

        with patch("setup_repo.cli.BackupManager") as mock_manager:
            mock_instance = Mock()
            mock_instance.restore_backup.return_value = True
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                backup_cli(args)

            mock_instance.restore_backup.assert_called_once_with("test-backup", None)

    def test_backup_cli_restore_missing_name(self):
        """バックアップ名未指定エラーテスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "restore"
        args.name = None
        args.target = None

        with patch("builtins.print") as mock_print:
            backup_cli(args)

        mock_print.assert_called_with("エラー: バックアップ名を指定してください")


class TestMonitorCLI:
    """監視CLI機能のテスト"""

    def test_monitor_cli_health_action(self):
        """ヘルスチェックテスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "health"
        args.output = None

        with patch("setup_repo.cli.MonitorManager") as mock_manager:
            mock_instance = Mock()
            mock_instance.run_health_check.return_value = {
                "overall_status": "healthy",
                "timestamp": "2025-01-27T10:00:00Z",
                "system": {"platform": "Linux", "architecture": "x86_64", "python_version": "Python 3.11.0"},
                "resources": {
                    "cpu_usage_percent": 25.0,
                    "memory_usage_percent": 60.0,
                    "memory_used_gb": 4.8,
                    "memory_total_gb": 8.0,
                    "disk_usage_percent": 45.0,
                    "disk_used_gb": 90.0,
                    "disk_total_gb": 200.0,
                },
                "dependencies": {
                    "uv_available": True,
                    "git_available": True,
                    "python_version_supported": True,
                    "required_tools": {
                        "ruff": {"available": True, "version": "0.1.0"},
                        "mypy": {"available": True, "version": "1.0.0"},
                        "pyright": {"available": True, "version": "1.0.0"},
                    },
                },
                "project": {
                    "config_exists": True,
                    "pyproject_exists": True,
                    "git_repo": True,
                    "quality_metrics": {
                        "quality_score": 85.0,
                        "test_coverage": 90.0,
                        "ruff_issues": 0,
                        "mypy_errors": 0,
                        "pyright_errors": 0,
                        "security_vulnerabilities": 0,
                    },
                },
                "issues": [],
                "recommendations": ["Keep up the good work"],
            }
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                monitor_cli(args)

            mock_instance.run_health_check.assert_called_once()

    def test_monitor_cli_performance_action(self):
        """パフォーマンス監視テスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "performance"

        with patch("setup_repo.cli.MonitorManager") as mock_manager:
            mock_instance = Mock()
            mock_instance.run_performance_monitoring.return_value = {
                "timestamp": "2025-01-27T10:00:00Z",
                "system_performance": {
                    "cpu_count": 4,
                    "cpu_usage": "25.0%",
                    "memory": {"percent": 60.0, "available": 3.2 * (1024**3)},
                },
                "project_performance": {
                    "file_count": 150,
                    "total_size": 50 * (1024**2),
                    "python_files": 45,
                    "test_files": 30,
                },
            }
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                monitor_cli(args)

            mock_instance.run_performance_monitoring.assert_called_once()

    def test_monitor_cli_alerts_action(self):
        """アラートチェックテスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "alerts"

        with patch("setup_repo.cli.MonitorManager") as mock_manager:
            mock_instance = Mock()
            mock_instance.run_alert_check.return_value = [
                {
                    "severity": "warning",
                    "type": "resource",
                    "message": "CPU使用率が高くなっています",
                    "timestamp": "2025-01-27T10:00:00Z",
                }
            ]
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                monitor_cli(args)

            mock_instance.run_alert_check.assert_called_once()

    def test_monitor_cli_dashboard_action(self):
        """ダッシュボードデータ生成テスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "dashboard"
        args.output = None

        with (
            patch("setup_repo.cli.MonitorManager") as mock_manager,
            patch("setup_repo.cli.safe_path_join") as mock_path_join,
            patch("builtins.open"),
        ):
            mock_path_join.side_effect = [Path.cwd(), Path("output"), Path("output/dashboard.json")]
            mock_instance = Mock()
            mock_instance.generate_dashboard_data.return_value = {
                "summary": {
                    "overall_status": "healthy",
                    "active_alerts": 0,
                    "cpu_usage": 25.0,
                    "memory_usage": 60.0,
                    "disk_usage": 45.0,
                }
            }
            mock_manager.return_value = mock_instance

            with patch("builtins.print"):
                monitor_cli(args)

            mock_instance.generate_dashboard_data.assert_called_once()

    def test_monitor_cli_invalid_action(self):
        """不正なアクションエラーテスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "invalid"

        with patch("builtins.print") as mock_print:
            monitor_cli(args)

        expected_msg = "エラー: 不正なアクション。health/performance/alerts/dashboard のいずれかを指定してください"
        mock_print.assert_called_with(expected_msg)

    def test_monitor_cli_health_with_output_file_error(self):
        """ヘルスチェック出力ファイル保存エラーテスト"""
        verify_current_platform()

        args = Mock()
        args.project_root = None
        args.action = "health"
        args.output = "health-report.json"

        with (
            patch("setup_repo.cli.MonitorManager") as mock_manager,
            patch("setup_repo.cli.safe_path_join") as mock_path_join,
            patch("builtins.open", side_effect=OSError("Permission denied")),
        ):
            mock_path_join.side_effect = [Path.cwd(), Path("output"), Path("output/health-report.json")]
            mock_instance = Mock()
            mock_instance.run_health_check.return_value = {
                "overall_status": "healthy",
                "timestamp": "2025-01-27T10:00:00Z",
                "system": {"platform": "Linux", "architecture": "x86_64", "python_version": "Python 3.11.0"},
                "resources": {
                    "cpu_usage_percent": 25.0,
                    "memory_usage_percent": 60.0,
                    "memory_used_gb": 4.8,
                    "memory_total_gb": 8.0,
                    "disk_usage_percent": 45.0,
                    "disk_used_gb": 90.0,
                    "disk_total_gb": 200.0,
                },
                "dependencies": {
                    "uv_available": True,
                    "git_available": True,
                    "python_version_supported": True,
                    "required_tools": {},
                },
                "project": {"config_exists": True, "pyproject_exists": True, "git_repo": True, "quality_metrics": None},
                "issues": [],
                "recommendations": [],
            }
            mock_manager.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                monitor_cli(args)

            # エラーメッセージが出力されることを確認
            mock_print.assert_any_call("エラー: 出力ファイルの保存に失敗しました: Permission denied")

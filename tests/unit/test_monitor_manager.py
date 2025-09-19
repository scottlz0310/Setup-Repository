"""monitor_manager.py のテスト"""

import platform
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from setup_repo.monitor_manager import AlertManager, MonitorManager, PerformanceMonitor, SystemHealthChecker


class TestSystemHealthChecker:
    """SystemHealthChecker のテスト"""

    def test_init(self, tmp_path):
        """初期化テスト"""
        checker = SystemHealthChecker(tmp_path)
        assert checker.project_root == tmp_path

    def test_init_default_path(self):
        """デフォルトパス初期化テスト"""
        checker = SystemHealthChecker()
        assert checker.project_root == Path.cwd()

    @patch("setup_repo.monitor_manager.psutil")
    def test_check_system_health(self, mock_psutil, tmp_path):
        """システムヘルスチェックテスト"""
        # psutilのモック設定
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.virtual_memory.return_value = MagicMock(total=8 * 1024**3, used=4 * 1024**3, percent=50.0)
        mock_psutil.disk_usage.return_value = MagicMock(total=100 * 1024**3, used=50 * 1024**3)

        checker = SystemHealthChecker(tmp_path)

        with (
            patch.object(checker, "_check_dependencies") as mock_deps,
            patch.object(checker, "_check_project_health") as mock_project,
        ):
            mock_deps.return_value = {
                "uv_available": True,
                "git_available": True,
                "python_version_supported": True,
                "required_tools": {"ruff": {"available": True, "version": "0.1.0"}},
            }
            mock_project.return_value = {
                "config_exists": True,
                "pyproject_exists": True,
                "git_repo": True,
                "quality_metrics": None,
            }

            health_data = checker.check_system_health()

            assert "timestamp" in health_data
            assert "system" in health_data
            assert "resources" in health_data
            assert "dependencies" in health_data
            assert "project" in health_data
            assert health_data["overall_status"] == "healthy"

    def test_check_system_info(self, tmp_path):
        """システム情報チェックテスト"""
        checker = SystemHealthChecker(tmp_path)
        system_info = checker._check_system_info()

        assert system_info["platform"] == platform.system()
        assert system_info["python_version"] == sys.version
        assert "architecture" in system_info
        assert "hostname" in system_info

    @patch("setup_repo.monitor_manager.psutil")
    def test_check_system_resources(self, mock_psutil, tmp_path):
        """システムリソースチェックテスト"""
        mock_psutil.cpu_percent.return_value = 75.0
        mock_psutil.virtual_memory.return_value = MagicMock(total=16 * 1024**3, used=8 * 1024**3, percent=50.0)
        mock_psutil.disk_usage.return_value = MagicMock(total=500 * 1024**3, used=100 * 1024**3)

        checker = SystemHealthChecker(tmp_path)
        resources = checker._check_system_resources()

        assert resources["cpu_usage_percent"] == 75.0
        assert resources["memory_usage_percent"] == 50.0
        assert resources["disk_usage_percent"] == 20.0

    @patch("setup_repo.monitor_manager.shutil.which")
    @patch("setup_repo.monitor_manager.subprocess.run")
    def test_check_dependencies(self, mock_run, mock_which, tmp_path):
        """依存関係チェックテスト"""
        mock_which.side_effect = lambda x: "/usr/bin/" + x if x in ["uv", "git"] else None
        mock_run.return_value = MagicMock(returncode=0, stdout="ruff 0.1.0")

        checker = SystemHealthChecker(tmp_path)
        deps = checker._check_dependencies()

        assert deps["uv_available"] is True
        assert deps["git_available"] is True
        assert deps["python_version_supported"] is True
        assert "required_tools" in deps

    def test_check_project_health(self, tmp_path):
        """プロジェクトヘルスチェックテスト"""
        # テスト用ファイル作成
        config_file = tmp_path / "config.local.json"
        config_file.write_text("{}")
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("[project]")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        checker = SystemHealthChecker(tmp_path)

        with patch("setup_repo.monitor_manager.QualityMetricsCollector") as mock_collector:
            mock_metrics = MagicMock()
            mock_metrics.get_quality_score.return_value = 85.0
            mock_metrics.test_coverage = 90.0
            mock_metrics.ruff_issues = 2
            mock_metrics.mypy_errors = 1
            mock_metrics.security_vulnerabilities = 0
            mock_collector.return_value.collect_all_metrics.return_value = mock_metrics

            project_health = checker._check_project_health()

            assert project_health["config_exists"] is True
            assert project_health["pyproject_exists"] is True
            assert project_health["git_repo"] is True
            assert project_health["quality_metrics"] is not None

    @patch("setup_repo.monitor_manager.psutil")
    def test_determine_overall_status_healthy(self, mock_psutil, tmp_path):
        """正常ステータス判定テスト"""
        mock_psutil.cpu_percent.return_value = 30.0
        mock_psutil.virtual_memory.return_value = MagicMock(percent=40.0)
        mock_psutil.disk_usage.return_value = MagicMock(total=1000, used=300)

        checker = SystemHealthChecker(tmp_path)
        health_data = {
            "resources": {
                "cpu_usage_percent": 30.0,
                "memory_usage_percent": 40.0,
                "disk_usage_percent": 30.0,
            },
            "dependencies": {
                "uv_available": True,
                "git_available": True,
                "python_version_supported": True,
            },
            "project": {
                "config_exists": True,
                "quality_metrics": {"quality_score": 85.0},
            },
        }

        status = checker._determine_overall_status(health_data)
        assert status == "healthy"

    @patch("setup_repo.monitor_manager.psutil")
    def test_determine_overall_status_warning(self, mock_psutil, tmp_path):
        """警告ステータス判定テスト"""
        checker = SystemHealthChecker(tmp_path)
        health_data = {
            "resources": {
                "cpu_usage_percent": 85.0,  # 高CPU使用率
                "memory_usage_percent": 40.0,
                "disk_usage_percent": 30.0,
            },
            "dependencies": {
                "uv_available": True,
                "git_available": True,
                "python_version_supported": True,
            },
            "project": {
                "config_exists": True,
                "quality_metrics": {"quality_score": 85.0},
            },
        }

        status = checker._determine_overall_status(health_data)
        assert status == "warning"


class TestPerformanceMonitor:
    """PerformanceMonitor のテスト"""

    def test_init(self, tmp_path):
        """初期化テスト"""
        monitor = PerformanceMonitor(tmp_path)
        assert monitor.project_root == tmp_path
        assert monitor.monitor_dir.exists()

    @patch("setup_repo.monitor_manager.psutil")
    def test_collect_performance_metrics(self, mock_psutil, tmp_path):
        """パフォーマンスメトリクス収集テスト"""
        mock_psutil.cpu_count.return_value = 8
        mock_psutil.cpu_percent.return_value = [10, 20, 30, 40, 50, 60, 70, 80]
        mock_psutil.virtual_memory.return_value = MagicMock(total=16 * 1024**3, available=8 * 1024**3, percent=50.0)

        # JSON serializableなデータを返すモックを作成
        mock_disk_io = MagicMock()
        mock_disk_io._asdict.return_value = {"read_count": 100, "write_count": 50}
        mock_psutil.disk_io_counters.return_value = mock_disk_io

        mock_net_io = MagicMock()
        mock_net_io._asdict.return_value = {"bytes_sent": 1000, "bytes_recv": 2000}
        mock_psutil.net_io_counters.return_value = mock_net_io

        # テスト用ファイル作成
        (tmp_path / "test.py").write_text("print('hello')")
        (tmp_path / "test_example.py").write_text("def test_func(): pass")

        monitor = PerformanceMonitor(tmp_path)
        metrics = monitor.collect_performance_metrics()

        assert "timestamp" in metrics
        assert "system_performance" in metrics
        assert "project_performance" in metrics
        assert metrics["system_performance"]["cpu_count"] == 8
        assert metrics["project_performance"]["python_files"] >= 2

    def test_collect_project_metrics(self, tmp_path):
        """プロジェクトメトリクス収集テスト"""
        # テスト用ファイル作成
        (tmp_path / "main.py").write_text("print('main')")
        (tmp_path / "test_main.py").write_text("def test_main(): pass")
        (tmp_path / "README.md").write_text("# Test")

        monitor = PerformanceMonitor(tmp_path)
        metrics = monitor._collect_project_metrics()

        assert metrics["file_count"] >= 3
        assert metrics["python_files"] >= 2
        assert metrics["test_files"] >= 1
        assert metrics["total_size"] > 0


class TestAlertManager:
    """AlertManager のテスト"""

    def test_init(self, tmp_path):
        """初期化テスト"""
        manager = AlertManager(tmp_path)
        assert manager.project_root == tmp_path
        assert manager.alerts_dir.exists()

    def test_check_alerts_no_issues(self, tmp_path):
        """アラートなしテスト"""
        manager = AlertManager(tmp_path)
        health_data = {
            "resources": {
                "cpu_usage_percent": 50.0,
                "memory_usage_percent": 60.0,
                "disk_usage_percent": 70.0,
            },
            "project": {
                "quality_metrics": {
                    "quality_score": 85.0,
                    "security_vulnerabilities": 0,
                }
            },
        }

        alerts = manager.check_alerts(health_data)
        assert len(alerts) == 0

    def test_check_alerts_with_issues(self, tmp_path):
        """アラートありテスト"""
        manager = AlertManager(tmp_path)
        health_data = {
            "resources": {
                "cpu_usage_percent": 95.0,  # 危険レベル
                "memory_usage_percent": 98.0,  # 危険レベル
                "disk_usage_percent": 97.0,  # 危険レベル
            },
            "project": {
                "quality_metrics": {
                    "quality_score": 30.0,  # 低品質
                    "security_vulnerabilities": 5,  # セキュリティ問題
                }
            },
        }

        alerts = manager.check_alerts(health_data)
        assert len(alerts) >= 3  # CPU, メモリ, ディスクアラート

        # アラートタイプの確認
        alert_types = [alert["type"] for alert in alerts]
        assert "resource" in alert_types
        assert "quality" in alert_types or "security" in alert_types


class TestMonitorManager:
    """MonitorManager のテスト"""

    def test_init(self, tmp_path):
        """初期化テスト"""
        manager = MonitorManager(tmp_path)
        assert manager.project_root == tmp_path
        assert isinstance(manager.health_checker, SystemHealthChecker)
        assert isinstance(manager.performance_monitor, PerformanceMonitor)
        assert isinstance(manager.alert_manager, AlertManager)

    @patch("setup_repo.monitor_manager.psutil")
    def test_run_health_check(self, mock_psutil, tmp_path):
        """ヘルスチェック実行テスト"""
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.virtual_memory.return_value = MagicMock(total=8 * 1024**3, used=4 * 1024**3, percent=50.0)
        mock_psutil.disk_usage.return_value = MagicMock(total=100 * 1024**3, used=50 * 1024**3)

        manager = MonitorManager(tmp_path)

        with (
            patch.object(manager.health_checker, "_check_dependencies") as mock_deps,
            patch.object(manager.health_checker, "_check_project_health") as mock_project,
        ):
            mock_deps.return_value = {
                "uv_available": True,
                "git_available": True,
                "python_version_supported": True,
                "required_tools": {},
            }
            mock_project.return_value = {
                "config_exists": True,
                "pyproject_exists": True,
                "git_repo": True,
                "quality_metrics": None,
            }

            health_data = manager.run_health_check()
            assert "overall_status" in health_data

    @patch("setup_repo.monitor_manager.psutil")
    def test_generate_dashboard_data(self, mock_psutil, tmp_path):
        """ダッシュボードデータ生成テスト"""
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.virtual_memory.return_value = MagicMock(
            total=8 * 1024**3, used=4 * 1024**3, percent=50.0, available=4 * 1024**3
        )
        mock_psutil.disk_usage.return_value = MagicMock(total=100 * 1024**3, used=50 * 1024**3)
        mock_psutil.disk_io_counters.return_value = None
        mock_psutil.net_io_counters.return_value = None

        manager = MonitorManager(tmp_path)

        with (
            patch.object(manager.health_checker, "_check_dependencies") as mock_deps,
            patch.object(manager.health_checker, "_check_project_health") as mock_project,
        ):
            mock_deps.return_value = {
                "uv_available": True,
                "git_available": True,
                "python_version_supported": True,
                "required_tools": {},
            }
            mock_project.return_value = {
                "config_exists": True,
                "pyproject_exists": True,
                "git_repo": True,
                "quality_metrics": None,
            }

            dashboard_data = manager.generate_dashboard_data()

            assert "timestamp" in dashboard_data
            assert "health" in dashboard_data
            assert "performance" in dashboard_data
            assert "alerts" in dashboard_data
            assert "summary" in dashboard_data

            summary = dashboard_data["summary"]
            assert "overall_status" in summary
            assert "active_alerts" in summary
            assert "cpu_usage" in summary
            assert "memory_usage" in summary
            assert "disk_usage" in summary

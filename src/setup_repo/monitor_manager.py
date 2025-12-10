"""システム監視・ヘルスチェック管理"""

import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from .quality_metrics import QualityMetricsCollector
from .security_helpers import safe_path_join
from .utils import ensure_directory


class SystemHealthChecker:
    """システムヘルスチェッククラス"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()

    def check_system_health(self) -> dict[str, Any]:
        """システム全体のヘルスチェック"""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "system": self._check_system_info(),
            "resources": self._check_system_resources(),
            "dependencies": self._check_dependencies(),
            "project": self._check_project_health(),
            "overall_status": "healthy",
            "issues": [],
            "recommendations": [],
        }

        # 全体ステータス判定
        health_data["overall_status"] = self._determine_overall_status(health_data)
        return health_data

    def _check_system_info(self) -> dict[str, Any]:
        """システム情報チェック"""
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": sys.version,
            "hostname": platform.node(),
        }

    def _check_system_resources(self) -> dict[str, Any]:
        """システムリソースチェック"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(self.project_root))

        resources = {
            "cpu_usage_percent": cpu_percent,
            "memory_total_gb": memory.total / (1024**3),
            "memory_used_gb": memory.used / (1024**3),
            "memory_usage_percent": memory.percent,
            "disk_total_gb": disk.total / (1024**3),
            "disk_used_gb": disk.used / (1024**3),
            "disk_usage_percent": (disk.used / disk.total) * 100,
        }

        return resources

    def _check_dependencies(self) -> dict[str, Any]:
        """依存関係チェック"""
        dependencies: dict[str, Any] = {
            "uv_available": shutil.which("uv") is not None,
            "git_available": shutil.which("git") is not None,
            "python_version_supported": sys.version_info >= (3, 9),
            "required_tools": {},
        }

        # 必要ツールの確認
        tools = ["ruff", "basedpyright", "pytest"]
        for tool in tools:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", tool, "--version"], capture_output=True, text=True, timeout=10
                )
                tool_info = {
                    "available": result.returncode == 0,
                    "version": result.stdout.strip() if result.returncode == 0 else None,
                }
                dependencies["required_tools"][tool] = tool_info
            except (subprocess.TimeoutExpired, FileNotFoundError):
                tool_info = {"available": False, "version": None}
                dependencies["required_tools"][tool] = tool_info

        return dependencies

    def _check_project_health(self) -> dict[str, Any]:
        """プロジェクト固有のヘルスチェック"""
        project_health: dict[str, Any] = {
            "config_exists": False,
            "pyproject_exists": False,
            "git_repo": False,
            "quality_metrics": None,
        }

        # 設定ファイル確認
        config_file = safe_path_join(self.project_root, "config.local.json")
        project_health["config_exists"] = config_file.exists()

        # pyproject.toml確認
        pyproject_file = safe_path_join(self.project_root, "pyproject.toml")
        project_health["pyproject_exists"] = pyproject_file.exists()

        # Gitリポジトリ確認
        git_dir = safe_path_join(self.project_root, ".git")
        project_health["git_repo"] = git_dir.exists()

        # 品質メトリクス取得
        try:
            collector = QualityMetricsCollector(self.project_root)
            metrics = collector.collect_all_metrics()
            quality_metrics = {
                "quality_score": metrics.get_quality_score(),
                "test_coverage": metrics.test_coverage,
                "ruff_issues": metrics.ruff_issues,
                "pyright_errors": getattr(metrics, "pyright_errors", metrics.mypy_errors),
                "mypy_errors": metrics.mypy_errors,
                "security_vulnerabilities": metrics.security_vulnerabilities,
            }
            project_health["quality_metrics"] = quality_metrics
        except Exception:
            project_health["quality_metrics"] = None

        return project_health

    def _determine_overall_status(self, health_data: dict[str, Any]) -> str:
        """全体ステータスを判定"""
        issues = []
        recommendations = []

        # リソース使用量チェック
        resources = health_data["resources"]
        if resources["cpu_usage_percent"] > 80:
            issues.append("CPU使用率が高い (>80%)")
            recommendations.append("CPU集約的なプロセスを確認してください")

        if resources["memory_usage_percent"] > 85:
            issues.append("メモリ使用率が高い (>85%)")
            recommendations.append("メモリ使用量を最適化してください")

        if resources["disk_usage_percent"] > 90:
            issues.append("ディスク使用率が高い (>90%)")
            recommendations.append("不要なファイルを削除してください")

        # 依存関係チェック
        deps = health_data["dependencies"]
        if not deps["uv_available"]:
            issues.append("uvが利用できません")
            recommendations.append("uvをインストールしてください")

        if not deps["git_available"]:
            issues.append("Gitが利用できません")
            recommendations.append("Gitをインストールしてください")

        if not deps["python_version_supported"]:
            issues.append("Pythonバージョンが古い (<3.9)")
            recommendations.append("Python 3.9以上にアップグレードしてください")

        # プロジェクトヘルスチェック
        project = health_data["project"]
        if not project["config_exists"]:
            issues.append("設定ファイルが見つかりません")
            recommendations.append("python main.py setup を実行してください")

        if project["quality_metrics"]:
            quality_score = project["quality_metrics"]["quality_score"]
            if quality_score < 70:
                issues.append(f"品質スコアが低い ({quality_score:.1f}/100)")
                recommendations.append("コード品質の改善を検討してください")

        health_data["issues"] = issues
        health_data["recommendations"] = recommendations

        if len(issues) == 0:
            return "healthy"
        elif len(issues) <= 2:
            return "warning"
        else:
            return "critical"


class PerformanceMonitor:
    """パフォーマンス監視クラス"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.monitor_dir = safe_path_join(self.project_root, "output/monitoring")
        ensure_directory(self.monitor_dir)

    def collect_performance_metrics(self) -> dict[str, Any]:
        """パフォーマンスメトリクス収集"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system_performance": self._collect_system_metrics(),
            "project_performance": self._collect_project_metrics(),
        }

        # メトリクス保存
        self._save_metrics(metrics)
        return metrics

    def _collect_system_metrics(self) -> dict[str, Any]:
        """システムパフォーマンスメトリクス"""
        try:
            disk_io_data = psutil.disk_io_counters()
            disk_io_dict = disk_io_data._asdict() if disk_io_data is not None else {}
        except Exception:
            disk_io_dict = {}

        try:
            network_io_data = psutil.net_io_counters()
            network_io_dict = network_io_data._asdict() if network_io_data is not None else {}
        except Exception:
            network_io_dict = {}

        return {
            "cpu_count": psutil.cpu_count(),
            "cpu_usage": psutil.cpu_percent(interval=1, percpu=True),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk_io": disk_io_dict,
            "network_io": network_io_dict,
        }

    def _collect_project_metrics(self) -> dict[str, Any]:
        """プロジェクトパフォーマンスメトリクス"""
        metrics = {
            "file_count": 0,
            "total_size": 0,
            "python_files": 0,
            "test_files": 0,
        }

        try:
            for file_path in self.project_root.rglob("*"):
                if file_path.is_file():
                    metrics["file_count"] += 1
                    metrics["total_size"] += file_path.stat().st_size

                    if file_path.suffix == ".py":
                        metrics["python_files"] += 1
                        if "test" in file_path.name.lower():
                            metrics["test_files"] += 1
        except (OSError, PermissionError):
            # ファイルアクセス権限エラーは無視（メトリクス収集は継続）
            pass  # nosec B110

        return metrics

    def _save_metrics(self, metrics: dict[str, Any]) -> None:
        """メトリクスをファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = safe_path_join(self.monitor_dir, f"performance_{timestamp}.json")

        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)


class AlertManager:
    """アラート管理クラス"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.alerts_dir = safe_path_join(self.project_root, "output/alerts")
        ensure_directory(self.alerts_dir)

    def check_alerts(self, health_data: dict[str, Any]) -> list[dict[str, Any]]:
        """アラート条件をチェック"""
        alerts = []

        # リソースアラート
        resources = health_data["resources"]
        if resources["cpu_usage_percent"] > 90:
            alerts.append(
                {
                    "type": "resource",
                    "severity": "critical",
                    "message": f"CPU使用率が危険レベル: {resources['cpu_usage_percent']:.1f}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        if resources["memory_usage_percent"] > 95:
            alerts.append(
                {
                    "type": "resource",
                    "severity": "critical",
                    "message": f"メモリ使用率が危険レベル: {resources['memory_usage_percent']:.1f}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        if resources["disk_usage_percent"] > 95:
            alerts.append(
                {
                    "type": "resource",
                    "severity": "critical",
                    "message": f"ディスク使用率が危険レベル: {resources['disk_usage_percent']:.1f}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 品質アラート
        project = health_data["project"]
        if project["quality_metrics"]:
            quality_score = project["quality_metrics"]["quality_score"]
            if quality_score < 50:
                alerts.append(
                    {
                        "type": "quality",
                        "severity": "warning",
                        "message": f"品質スコアが低下: {quality_score:.1f}/100",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            security_vulns = project["quality_metrics"]["security_vulnerabilities"]
            if security_vulns > 0:
                alerts.append(
                    {
                        "type": "security",
                        "severity": "high",
                        "message": f"セキュリティ脆弱性を検出: {security_vulns}件",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # アラート保存
        if alerts:
            self._save_alerts(alerts)

        return alerts

    def _save_alerts(self, alerts: list[dict[str, Any]]) -> None:
        """アラートをファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        alerts_file = safe_path_join(self.alerts_dir, f"alerts_{timestamp}.json")

        with open(alerts_file, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)


class MonitorManager:
    """監視管理統合クラス"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.health_checker = SystemHealthChecker(project_root)
        self.performance_monitor = PerformanceMonitor(project_root)
        self.alert_manager = AlertManager(project_root)

    def run_health_check(self) -> dict[str, Any]:
        """ヘルスチェック実行"""
        return self.health_checker.check_system_health()

    def run_performance_monitoring(self) -> dict[str, Any]:
        """パフォーマンス監視実行"""
        return self.performance_monitor.collect_performance_metrics()

    def run_alert_check(self) -> list[dict[str, Any]]:
        """アラートチェック実行"""
        health_data = self.run_health_check()
        return self.alert_manager.check_alerts(health_data)

    def generate_dashboard_data(self) -> dict[str, Any]:
        """ダッシュボード用データ生成"""
        health_data = self.run_health_check()
        performance_data = self.run_performance_monitoring()
        alerts = self.run_alert_check()

        return {
            "timestamp": datetime.now().isoformat(),
            "health": health_data,
            "performance": performance_data,
            "alerts": alerts,
            "summary": {
                "overall_status": health_data["overall_status"],
                "active_alerts": len(alerts),
                "cpu_usage": health_data["resources"]["cpu_usage_percent"],
                "memory_usage": health_data["resources"]["memory_usage_percent"],
                "disk_usage": health_data["resources"]["disk_usage_percent"],
            },
        }

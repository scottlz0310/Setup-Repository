"""
品質ツール固有のデータ収集機能

このモジュールは、各品質ツール（ruff、mypy、pytest）との
連携とデータ収集機能を提供します。
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional, Union

from .quality_logger import QualityLogger, get_quality_logger
from .quality_errors import (
    CoverageError,
    MyPyError,
    RuffError,
    SecurityScanError,
    TestFailureError,
)


class QualityToolCollector:
    """品質ツール固有のデータ収集クラス"""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        logger: Optional[QualityLogger] = None,
    ) -> None:
        self.project_root = project_root or Path.cwd()
        self.logger = logger or get_quality_logger()


def collect_ruff_metrics(
    project_root: Optional[Path] = None,
    logger: Optional[QualityLogger] = None,
) -> dict[str, Any]:
    """Ruffリンティングメトリクスを収集"""
    project_root = project_root or Path.cwd()
    logger = logger or get_quality_logger()
    
    logger.log_quality_check_start("Ruff")

    try:
        # Ruffチェック実行
        result = subprocess.run(
            ["uv", "run", "ruff", "check", ".", "--output-format=json"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.stdout:
            issues = json.loads(result.stdout)
            issue_count = len(issues)
        else:
            issues = []
            issue_count = 0

        success = result.returncode == 0

        metrics_result = {
            "success": success,
            "issue_count": issue_count,
            "issues": issues,
            "errors": (
                []
                if success
                else [f"Ruffチェックで{issue_count}件の問題が見つかりました"]
            ),
        }

        if success:
            logger.log_quality_check_success(
                "Ruff", {"issue_count": issue_count}
            )
        else:
            error = RuffError(
                f"Ruffリンティングで{issue_count}件の問題が見つかりました", issues
            )
            logger.log_quality_check_failure("Ruff", error)

        return metrics_result

    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        FileNotFoundError,
    ) as e:
        error = RuffError(f"Ruffメトリクス収集エラー: {str(e)}")
        logger.log_quality_check_failure("Ruff", error)
        return {"success": False, "issue_count": 0, "errors": [str(e)]}


def collect_mypy_metrics(
    project_root: Optional[Path] = None,
    logger: Optional[QualityLogger] = None,
) -> dict[str, Any]:
    """MyPy型チェックメトリクスを収集"""
    project_root = project_root or Path.cwd()
    logger = logger or get_quality_logger()
    
    logger.log_quality_check_start("MyPy")

    try:
        # MyPyチェック実行
        result = subprocess.run(
            ["uv", "run", "mypy", "src/", "--no-error-summary"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        # エラー行数をカウント
        error_lines = [
            line
            for line in result.stdout.split("\n")
            if line.strip() and "error:" in line
        ]
        error_count = len(error_lines)

        success = result.returncode == 0

        metrics_result = {
            "success": success,
            "error_count": error_count,
            "error_details": error_lines[:10],  # 最初の10個のエラーを保存
            "errors": (
                []
                if success
                else [f"MyPyで{error_count}件のエラーが見つかりました"]
            ),
        }

        if success:
            logger.log_quality_check_success(
                "MyPy", {"error_count": error_count}
            )
        else:
            error = MyPyError(
                f"MyPy型チェックで{error_count}件のエラーが見つかりました",
                error_lines,
            )
            logger.log_quality_check_failure("MyPy", error)

        return metrics_result

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        error = MyPyError(f"MyPyメトリクス収集エラー: {str(e)}")
        logger.log_quality_check_failure("MyPy", error)
        return {"success": False, "error_count": 0, "errors": [str(e)]}


def collect_pytest_metrics(
    project_root: Optional[Path] = None,
    logger: Optional[QualityLogger] = None,
    parallel_workers: Union[str, int] = "auto",
) -> dict[str, Any]:
    """テストメトリクスを収集（並列実行対応）"""
    project_root = project_root or Path.cwd()
    logger = logger or get_quality_logger()
    
    logger.log_quality_check_start("Tests")

    try:
        # 並列実行用のコマンドを構築
        cmd = [
            "uv",
            "run",
            "pytest",
            "--cov=src/setup_repo",
            "--cov-report=json",
            "--json-report",
            "--json-report-file=test-report.json",
        ]

        # 並列実行設定
        if parallel_workers != "1" and parallel_workers != 1:
            if parallel_workers == "auto":
                import os

                cpu_count = os.cpu_count() or 4
                workers = max(1, int(cpu_count * 0.75))
            else:
                workers = (
                    int(parallel_workers)
                    if isinstance(parallel_workers, str)
                    else parallel_workers
                )

            if workers > 1:
                cmd.extend(["-n", str(workers), "--dist", "worksteal"])
                logger.info(f"並列テスト実行: {workers}ワーカー")

        # Pytestでカバレッジ付きテスト実行
        result = subprocess.run(
            cmd, cwd=project_root, capture_output=True, text=True, check=False
        )

        # カバレッジ情報を読み取り
        coverage_file = project_root / "coverage.json"
        coverage_percent = 0.0
        if coverage_file.exists():
            try:
                with open(coverage_file, encoding="utf-8") as f:
                    coverage_data = json.load(f)
                    coverage_percent = coverage_data.get("totals", {}).get(
                        "percent_covered", 0.0
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        # テスト結果を読み取り
        test_report_file = project_root / "test-report.json"
        passed = failed = 0
        failed_tests = []
        if test_report_file.exists():
            try:
                with open(test_report_file, encoding="utf-8") as f:
                    test_data = json.load(f)
                    summary = test_data.get("summary", {})
                    passed = summary.get("passed", 0)
                    failed = summary.get("failed", 0)

                    # 失敗したテストの詳細を取得
                    for test in test_data.get("tests", []):
                        if test.get("outcome") == "failed":
                            failed_tests.append(test.get("nodeid", "unknown"))

            except (json.JSONDecodeError, KeyError):
                pass

        success = result.returncode == 0 and failed == 0

        metrics_result = {
            "success": success,
            "coverage_percent": coverage_percent,
            "tests_passed": passed,
            "tests_failed": failed,
            "failed_tests": failed_tests,
            "errors": [] if success else [f"テストで{failed}件の失敗がありました"],
        }

        if success:
            logger.log_quality_check_success(
                "Tests",
                {"coverage": coverage_percent, "passed": passed, "failed": failed},
            )
        else:
            # カバレッジ不足の場合は専用エラー
            if coverage_percent < 80.0:
                logger.log_quality_check_failure(
                    "Tests",
                    CoverageError(
                        f"カバレッジが不足しています: "
                        f"{coverage_percent:.1f}% (必要: 80.0%)",
                        coverage_percent,
                        80.0,
                    ),
                )
            else:
                test_error = TestFailureError(
                    f"テストで{failed}件の失敗がありました",
                    failed_tests,
                    coverage_percent,
                )
                logger.log_quality_check_failure("Tests", test_error)

        return metrics_result

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        test_error = TestFailureError(f"テストメトリクス収集エラー: {str(e)}")
        logger.log_quality_check_failure("Tests", test_error)
        return {
            "success": False,
            "coverage_percent": 0.0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [str(e)],
        }


def collect_coverage_metrics(
    project_root: Optional[Path] = None,
    logger: Optional[QualityLogger] = None,
) -> dict[str, Any]:
    """カバレッジメトリクスを収集"""
    project_root = project_root or Path.cwd()
    logger = logger or get_quality_logger()
    
    coverage_file = project_root / "coverage.json"
    
    if not coverage_file.exists():
        return {
            "success": False,
            "coverage_percent": 0.0,
            "errors": ["カバレッジファイルが見つかりません"]
        }
    
    try:
        with open(coverage_file, encoding="utf-8") as f:
            coverage_data = json.load(f)
            coverage_percent = coverage_data.get("totals", {}).get(
                "percent_covered", 0.0
            )
        
        return {
            "success": True,
            "coverage_percent": coverage_percent,
            "coverage_data": coverage_data,
            "errors": []
        }
    
    except (json.JSONDecodeError, KeyError) as e:
        return {
            "success": False,
            "coverage_percent": 0.0,
            "errors": [f"カバレッジデータ解析エラー: {str(e)}"]
        }


def parse_tool_output(
    tool_name: str,
    output: str,
    output_format: str = "text",
) -> dict[str, Any]:
    """ツール出力を解析して構造化データに変換"""
    if output_format == "json":
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"error": f"{tool_name}のJSON出力解析に失敗しました"}
    
    # テキスト形式の場合は行ごとに分割
    lines = [line.strip() for line in output.split("\n") if line.strip()]
    
    if tool_name.lower() == "ruff":
        # Ruffのテキスト出力を解析
        issues = []
        for line in lines:
            # Ruffの出力形式: file.py:line:col: CODE message
            if ":" in line and any(code in line for code in ["E", "F", "W", "C", "N"]):
                issues.append(line)
        return {"issues": issues, "issue_count": len(issues)}
    
    elif tool_name.lower() == "mypy":
        # MyPyのテキスト出力を解析
        errors = [line for line in lines if "error:" in line]
        return {"errors": errors, "error_count": len(errors)}
    
    else:
        # 汎用的な解析
        return {"output_lines": lines, "line_count": len(lines)}
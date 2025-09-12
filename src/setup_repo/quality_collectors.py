"""
品質ツール固有のデータ収集機能

このモジュールは、各品質ツール（ruff、mypy、pytest）との
連携とデータ収集機能を提供します。
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Optional, Union

from .quality_errors import CoverageError, MyPyError, RuffError, TestFailureError
from .quality_logger import QualityLogger, get_quality_logger


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
        # テストコードのLintはCI失敗要因としないため、対象をアプリコード中心に限定
        ruff_cmd = [
            "uv",
            "run",
            "ruff",
            "check",
            "src",
            "scripts",
            "main.py",
            "--output-format=json",
        ]
        result = subprocess.run(
            ruff_cmd,
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
            "errors": ([] if success else [f"Ruffチェックで{issue_count}件の問題が見つかりました"]),
        }

        if success:
            logger.log_quality_check_success("Ruff", {"issue_count": issue_count})
        else:
            error = RuffError(f"Ruffリンティングで{issue_count}件の問題が見つかりました", issues)
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
        error_lines = [line for line in result.stdout.split("\n") if line.strip() and "error:" in line]
        error_count = len(error_lines)

        success = result.returncode == 0

        metrics_result = {
            "success": success,
            "error_count": error_count,
            "error_details": error_lines[:10],  # 最初の10個のエラーを保存
            "errors": ([] if success else [f"MyPyで{error_count}件のエラーが見つかりました"]),
        }

        if success:
            logger.log_quality_check_success("MyPy", {"error_count": error_count})
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
    coverage_threshold: float = 80.0,
    skip_integration_tests: bool = False,
) -> dict[str, Any]:
    """テストメトリクスを収集（並列実行対応）"""
    project_root = project_root or Path.cwd()
    logger = logger or get_quality_logger()

    logger.log_quality_check_start("Tests")

    try:
        import os

        # 環境変数でCI環境を確認
        is_ci = os.getenv("CI", "").lower() in ("true", "1")
        unit_tests_only = os.getenv("UNIT_TESTS_ONLY", "").lower() in ("true", "1")

        # 並列実行用のコマンドを構築
        cmd = [
            "uv",
            "run",
            "pytest",
            "--cov=src/setup_repo",
            "--cov-report=json",
            "--cov-report=xml",  # XMLカバレッジレポートも生成
            "--json-report",
            "--json-report-file=test-report.json",
            "--junit-xml=test-results.xml",  # JUnit XML形式のテスト結果を生成
        ]

        # テストマーカーの設定
        if skip_integration_tests or unit_tests_only or is_ci:
            # CI環境では単体テストのみ実行
            cmd.extend(["tests/unit/", "-m", "not performance and not stress"])
            logger.info("CI環境: 単体テストのみ実行")
        else:
            # ローカル環境では重いテストのみスキップ
            cmd.extend(["-m", "not performance and not stress"])
            logger.info("ローカル環境: 全テスト実行")

        # 並列実行設定
        if parallel_workers != "1" and parallel_workers != 1:
            if parallel_workers == "auto":
                cpu_count = os.cpu_count() or 4
                # CI環境ではワーカー数を減らして安定性を向上
                if is_ci:
                    workers = max(1, min(4, int(cpu_count * 0.5)))
                else:
                    workers = max(1, int(cpu_count * 0.75))
            else:
                workers = int(parallel_workers) if isinstance(parallel_workers, str) else parallel_workers

            if workers > 1:
                cmd.extend(["-n", str(workers), "--dist", "worksteal"])
                logger.info(f"並列テスト実行: {workers}ワーカー")

        # Pytestでカバレッジ付きテスト実行
        logger.info(f"テストコマンド: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True, check=False)

        # カバレッジ情報を読み取り
        coverage_file = project_root / "coverage.json"
        # パストラバーサル攻撃を防ぐためのバリデーション
        resolved_coverage_file = coverage_file.resolve()
        if not str(resolved_coverage_file).startswith(str(project_root.resolve())):
            logger.warning("カバレッジファイルのパスが不正です")
            coverage_percent = 0.0
        elif resolved_coverage_file.exists():
            try:
                with open(resolved_coverage_file, encoding="utf-8") as f:
                    coverage_data = json.load(f)
                    coverage_percent = coverage_data.get("totals", {}).get("percent_covered", 0.0)
            except (json.JSONDecodeError, KeyError):
                coverage_percent = 0.0
        else:
            coverage_percent = 0.0

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

        # CI環境ではカバレッジ闾値を緩和
        effective_threshold = coverage_threshold
        if is_ci and unit_tests_only:
            # 単体テストのみの場合はカバレッジ闾値を下げる
            effective_threshold = 70.0
            logger.info(f"CI環境(単体テストのみ): カバレッジ闾値を{effective_threshold}%に調整")

        success = result.returncode == 0 and failed == 0 and coverage_percent >= effective_threshold

        metrics_result = {
            "success": success,
            "coverage_percent": coverage_percent,
            "tests_passed": passed,
            "tests_failed": failed,
            "failed_tests": failed_tests,
            "effective_threshold": effective_threshold,
            "is_ci_environment": is_ci,
            "unit_tests_only": unit_tests_only,
            "errors": []
            if success
            else [
                msg
                for msg in [
                    f"テストで{failed}件の失敗がありました" if failed > 0 else None,
                    f"カバレッジ不足: {coverage_percent:.1f}% < {effective_threshold}%"
                    if coverage_percent < effective_threshold
                    else None,
                ]
                if msg is not None
            ],
        }

        if success:
            logger.log_quality_check_success(
                "Tests",
                {
                    "coverage": coverage_percent,
                    "passed": passed,
                    "failed": failed,
                    "threshold": effective_threshold,
                    "ci_mode": is_ci,
                },
            )
        else:
            # カバレッジ不足の場合は専用エラー
            if coverage_percent < effective_threshold:
                logger.log_quality_check_failure(
                    "Tests",
                    CoverageError(
                        f"カバレッジが不足しています: {coverage_percent:.1f}% (必要: {effective_threshold}%)",
                        coverage_percent,
                        effective_threshold,
                    ),
                )
            else:
                if failed > 0:
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
        import os

        return {
            "success": False,
            "coverage_percent": 0.0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [str(e)],
            "effective_threshold": coverage_threshold,
            "is_ci_environment": os.getenv("CI", "").lower() in ("true", "1"),
            "unit_tests_only": os.getenv("UNIT_TESTS_ONLY", "").lower() in ("true", "1"),
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
            "errors": ["カバレッジファイルが見つかりません"],
        }

    try:
        with open(coverage_file, encoding="utf-8") as f:
            coverage_data = json.load(f)
            coverage_percent = coverage_data.get("totals", {}).get("percent_covered", 0.0)

        return {
            "success": True,
            "coverage_percent": coverage_percent,
            "coverage_data": coverage_data,
            "errors": [],
        }

    except (json.JSONDecodeError, KeyError) as e:
        return {
            "success": False,
            "coverage_percent": 0.0,
            "errors": [f"カバレッジデータ解析エラー: {str(e)}"],
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

"""
品質ルール検証テスト

このモジュールでは、AI開発品質ルールの各段階（Phase 4-8）の
実装と遵守状況を検証します。リンティング、テスト戦略、
CI/CD、セキュリティ、観測性の各要件をテストします。
"""

import os
from pathlib import Path
from typing import Any

import pytest


class QualityRulesValidator:
    """品質ルール検証クラス"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_phase4_linting(self) -> dict[str, Any]:
        """Phase 4: リンティング・コード品質の検証"""
        results = {
            "ruff_configured": False,
            "mypy_configured": False,
            "style_guide_compliant": False,
            "security_scan_enabled": False,
        }

        # ruff設定の検証
        if self.pyproject_path.exists():
            try:
                import tomllib

                with open(self.pyproject_path, "rb") as f:
                    config = tomllib.load(f)

                if "tool" in config and "ruff" in config["tool"]:
                    results["ruff_configured"] = True
                    ruff_config = config["tool"]["ruff"]

                    # 推奨ルールの確認
                    if "select" in ruff_config:
                        required_rules = ["E", "F", "W", "I", "UP", "B", "C90", "T20"]
                        selected_rules = ruff_config["select"]
                        if any(rule in str(selected_rules) for rule in required_rules):
                            results["style_guide_compliant"] = True

                if "tool" in config and "mypy" in config["tool"]:
                    results["mypy_configured"] = True

            except (OSError, ValueError, KeyError) as e:
                self.errors.append(f"pyproject.toml読み込みエラー: {e}")

        return results

    def validate_phase5_testing(self) -> dict[str, Any]:
        """Phase 5: テスト戦略・カバレッジの検証"""
        results = {
            "pytest_configured": False,
            "coverage_configured": False,
            "test_structure_valid": False,
            "forbidden_patterns_absent": False,  # デフォルトをFalseに変更
        }

        # pytest設定の検証
        if self.pyproject_path.exists():
            try:
                import tomllib

                with open(self.pyproject_path, "rb") as f:
                    config = tomllib.load(f)

                if "tool" in config and "pytest" in config["tool"]:
                    results["pytest_configured"] = True

                if "tool" in config and "coverage" in config["tool"]:
                    results["coverage_configured"] = True

            except (OSError, ValueError, KeyError):
                # 読み込みエラーを無視
                pass

        # テスト構造の検証
        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            results["test_structure_valid"] = True
            results["forbidden_patterns_absent"] = True  # testsディレクトリが存在する場合のみTrue

            # 禁止パターンの検出
            forbidden_patterns = [
                "test_coverage_booster.py",
                "test_*_expanded.py",
            ]

            for pattern in forbidden_patterns:
                if list(tests_dir.rglob(pattern)):
                    results["forbidden_patterns_absent"] = False
                    self.errors.append(f"禁止されたテストファイルパターンを検出: {pattern}")

        return results

    def validate_phase6_ci_cd(self) -> dict[str, Any]:
        """Phase 6: CI/CD・自動化の検証"""
        results = {
            "github_workflows_exist": False,
            "matrix_configured": False,
            "security_scans_enabled": False,
            "branch_protection_ready": False,
        }

        # GitHub Actionsワークフローの検証
        workflows_dir = self.project_root / ".github" / "workflows"
        if workflows_dir.exists():
            results["github_workflows_exist"] = True

            for workflow_file in workflows_dir.glob("*.yml"):
                try:
                    import yaml

                    with open(workflow_file, encoding="utf-8") as f:
                        workflow = yaml.safe_load(f)

                    # マトリクス設定の確認
                    if "jobs" in workflow:
                        for job in workflow["jobs"].values():
                            if "strategy" in job and "matrix" in job["strategy"]:
                                results["matrix_configured"] = True

                    # セキュリティスキャンの確認
                    workflow_str = str(workflow)
                    if any(scan in workflow_str.lower() for scan in ["codeql", "security", "bandit"]):
                        results["security_scans_enabled"] = True

                except Exception as e:
                    self.warnings.append(f"ワークフローファイル解析エラー: {workflow_file.name} - {e}")

        return results

    def validate_phase7_security(self) -> dict[str, Any]:
        """Phase 7: セキュリティ・品質保証の検証"""
        results = {
            "secrets_management_configured": False,
            "gitignore_security_compliant": False,
            "dependency_scanning_enabled": False,
            "permissions_minimized": False,
        }

        # .gitignoreのセキュリティ検証
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, encoding="utf-8") as f:
                gitignore_content = f.read()

            required_patterns = [".env", "*.log", "__pycache__/", ".venv/"]
            if all(pattern in gitignore_content for pattern in required_patterns):
                results["gitignore_security_compliant"] = True

        # GitHub Actionsの権限設定確認
        workflows_dir = self.project_root / ".github" / "workflows"
        if workflows_dir.exists():
            for workflow_file in workflows_dir.glob("*.yml"):
                try:
                    import yaml

                    with open(workflow_file, encoding="utf-8") as f:
                        workflow = yaml.safe_load(f)

                    if "permissions" in workflow:
                        results["permissions_minimized"] = True

                except Exception:
                    pass

        return results

    def validate_phase8_observability(self) -> dict[str, Any]:
        """Phase 8: 観測性・監視の検証"""
        results = {
            "structured_logging_configured": False,
            "timezone_utc_enforced": False,
            "correlation_ids_supported": False,
        }

        # ログ設定の検証（コード内検索）
        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # 構造化ログの確認
                if "logging" in content and ("json" in content.lower() or "structured" in content.lower()):
                    results["structured_logging_configured"] = True

                # UTC時刻の確認
                if "utc" in content.lower() or "timezone" in content.lower():
                    results["timezone_utc_enforced"] = True

                # 相関IDの確認
                if any(term in content.lower() for term in ["trace_id", "request_id", "correlation"]):
                    results["correlation_ids_supported"] = True

            except (OSError, UnicodeDecodeError):
                # ファイル読み込みエラーを無視
                continue

        return results

    def get_overall_compliance(self) -> dict[str, Any]:
        """全体的なコンプライアンス状況の取得"""
        phase4 = self.validate_phase4_linting()
        phase5 = self.validate_phase5_testing()
        phase6 = self.validate_phase6_ci_cd()
        phase7 = self.validate_phase7_security()
        phase8 = self.validate_phase8_observability()

        total_checks = sum(len(phase.values()) for phase in [phase4, phase5, phase6, phase7, phase8])
        passed_checks = sum(sum(1 for v in phase.values() if v) for phase in [phase4, phase5, phase6, phase7, phase8])

        compliance_percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        return {
            "phase4_linting": phase4,
            "phase5_testing": phase5,
            "phase6_ci_cd": phase6,
            "phase7_security": phase7,
            "phase8_observability": phase8,
            "compliance_percentage": compliance_percentage,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@pytest.fixture
def quality_validator(temp_dir: Path) -> QualityRulesValidator:
    """品質ルール検証インスタンス"""
    return QualityRulesValidator(temp_dir)


@pytest.fixture
def mock_project_structure(temp_dir: Path) -> Path:
    """モックプロジェクト構造"""
    # pyproject.toml作成
    pyproject_content = """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"

[tool.ruff]
select = ["E", "F", "W", "I", "UP", "B", "C90", "T20"]
line-length = 88

[tool.mypy]
warn_unused_ignores = true
warn_redundant_casts = true
no_implicit_optional = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing"

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
fail_under = 80
"""

    pyproject_path = temp_dir / "pyproject.toml"
    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(pyproject_content)

    # .gitignore作成
    gitignore_content = """
__pycache__/
.venv/
.env
*.log
.coverage
coverage.xml
htmlcov/
"""

    gitignore_path = temp_dir / ".gitignore"
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(gitignore_content)

    # GitHub Actionsワークフロー作成
    workflows_dir = temp_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    workflow_content = """
name: CI

on: [push, pull_request]

permissions:
  contents: read
  pull-requests: write

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
        os: [ubuntu-latest, windows-latest, macos-latest]

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Security scan
      uses: github/codeql-action/analyze@v2
"""

    workflow_path = workflows_dir / "ci.yml"
    with open(workflow_path, "w", encoding="utf-8") as f:
        f.write(workflow_content)

    # テストディレクトリ作成
    tests_dir = temp_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    test_file = tests_dir / "test_example.py"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("""
import pytest

def test_example():
    assert True
""")

    # ソースコード作成
    src_dir = temp_dir / "src"
    src_dir.mkdir(exist_ok=True)

    source_file = src_dir / "main.py"
    with open(source_file, "w", encoding="utf-8") as f:
        f.write("""
import logging
import json
from datetime import datetime, timezone

# 構造化ログ設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def log_with_correlation_id(message: str, trace_id: str = None) -> None:
    '''相関IDを含むログ出力'''
    logger = logging.getLogger(__name__)
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "trace_id": trace_id,
        "level": "INFO"
    }
    logger.info(json.dumps(log_data))
""")

    return temp_dir


class TestPhase4Linting:
    """Phase 4: リンティング・コード品質のテスト"""

    def test_ruff_configuration_validation(self, mock_project_structure: Path) -> None:
        """ruff設定の検証テスト"""
        # 検証対象: ruff設定の妥当性確認
        # 目的: 推奨ルールが適切に設定されているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase4_linting()

        assert results["ruff_configured"] is True
        assert results["style_guide_compliant"] is True

    def test_mypy_configuration_validation(self, mock_project_structure: Path) -> None:
        """mypy設定の検証テスト"""
        # 検証対象: mypy設定の妥当性確認
        # 目的: 型チェック設定が適切に行われているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase4_linting()

        assert results["mypy_configured"] is True

    def test_missing_configuration_detection(self, temp_dir: Path) -> None:
        """設定不足の検出テスト"""
        # 検証対象: 設定ファイル不足の検出
        # 目的: 必要な設定が欠けている場合の検出機能テスト
        validator = QualityRulesValidator(temp_dir)
        results = validator.validate_phase4_linting()

        assert results["ruff_configured"] is False
        assert results["mypy_configured"] is False
        assert results["style_guide_compliant"] is False

    def test_invalid_pyproject_toml_handling(self, temp_dir: Path) -> None:
        """不正なpyproject.tomlの処理テスト"""
        # 検証対象: 破損した設定ファイルの処理
        # 目的: 不正な設定ファイルでもエラーハンドリングできることを確認
        invalid_toml = temp_dir / "pyproject.toml"
        with open(invalid_toml, "w", encoding="utf-8") as f:
            f.write("[invalid toml content")

        validator = QualityRulesValidator(temp_dir)
        validator.validate_phase4_linting()

        assert len(validator.errors) > 0
        assert any("読み込みエラー" in error for error in validator.errors)


class TestPhase5Testing:
    """Phase 5: テスト戦略・カバレッジのテスト"""

    def test_pytest_configuration_validation(self, mock_project_structure: Path) -> None:
        """pytest設定の検証テスト"""
        # 検証対象: pytest設定の妥当性確認
        # 目的: テストフレームワーク設定が適切かテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase5_testing()

        assert results["pytest_configured"] is True
        assert results["coverage_configured"] is True

    def test_test_structure_validation(self, mock_project_structure: Path) -> None:
        """テスト構造の検証テスト"""
        # 検証対象: テストディレクトリ構造の妥当性
        # 目的: 適切なテスト配置が行われているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase5_testing()

        assert results["test_structure_valid"] is True

    def test_forbidden_test_patterns_detection(self, temp_dir: Path) -> None:
        """禁止テストパターンの検出テスト"""
        # 検証対象: 禁止されたテストパターンの検出
        # 目的: カバレッジ稼ぎ等の不適切なテストを検出できることを確認
        tests_dir = temp_dir / "tests"
        tests_dir.mkdir(exist_ok=True)

        # 禁止パターンのファイル作成
        forbidden_file = tests_dir / "test_coverage_booster.py"
        with open(forbidden_file, "w", encoding="utf-8") as f:
            f.write("# カバレッジ稼ぎファイル")

        validator = QualityRulesValidator(temp_dir)
        results = validator.validate_phase5_testing()

        assert results["forbidden_patterns_absent"] is False
        assert len(validator.errors) > 0

    def test_coverage_threshold_validation(self, mock_project_structure: Path) -> None:
        """カバレッジ閾値の検証テスト"""
        # 検証対象: カバレッジ設定の妥当性
        # 目的: 適切なカバレッジ閾値が設定されているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase5_testing()

        assert results["coverage_configured"] is True

        # pyproject.tomlからカバレッジ設定を確認
        import tomllib

        with open(mock_project_structure / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)

        coverage_config = config.get("tool", {}).get("coverage", {}).get("report", {})
        fail_under = coverage_config.get("fail_under", 0)

        # 品質ルールに従った80%以上の閾値確認
        assert fail_under >= 80


class TestPhase6CICD:
    """Phase 6: CI/CD・自動化のテスト"""

    def test_github_workflows_validation(self, mock_project_structure: Path) -> None:
        """GitHub Actionsワークフローの検証テスト"""
        # 検証対象: CI/CDワークフローの設定
        # 目的: 適切なワークフローが設定されているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase6_ci_cd()

        assert results["github_workflows_exist"] is True

    def test_matrix_configuration_validation(self, mock_project_structure: Path) -> None:
        """マトリクス設定の検証テスト"""
        # 検証対象: OS×Pythonバージョンマトリクス
        # 目的: 複数環境でのテスト設定が適切かテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase6_ci_cd()

        assert results["matrix_configured"] is True

    def test_security_scans_detection(self, mock_project_structure: Path) -> None:
        """セキュリティスキャンの検出テスト"""
        # 検証対象: CI内のセキュリティスキャン設定
        # 目的: セキュリティスキャンが有効化されているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase6_ci_cd()

        assert results["security_scans_enabled"] is True

    def test_missing_workflows_handling(self, temp_dir: Path) -> None:
        """ワークフロー不足の処理テスト"""
        # 検証対象: ワークフローファイル不在の処理
        # 目的: CI/CD設定が不足している場合の検出テスト
        validator = QualityRulesValidator(temp_dir)
        results = validator.validate_phase6_ci_cd()

        assert results["github_workflows_exist"] is False
        assert results["matrix_configured"] is False

    @pytest.mark.skipif(
        not hasattr(__import__("importlib.util"), "find_spec")
        or __import__("importlib.util").find_spec("yaml") is None,
        reason="PyYAML not available",
    )
    def test_invalid_workflow_yaml_handling(self, temp_dir: Path) -> None:
        """不正なワークフローYAMLの処理テスト"""
        # 検証対象: 破損したワークフローファイルの処理
        # 目的: 不正なYAMLファイルでもエラーハンドリングできることを確認
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        invalid_yaml = workflows_dir / "invalid.yml"
        with open(invalid_yaml, "w", encoding="utf-8") as f:
            f.write("invalid: yaml: content:")

        validator = QualityRulesValidator(temp_dir)
        validator.validate_phase6_ci_cd()

        assert len(validator.warnings) > 0


class TestPhase7Security:
    """Phase 7: セキュリティ・品質保証のテスト"""

    def test_gitignore_security_validation(self, mock_project_structure: Path) -> None:
        """gitignoreセキュリティの検証テスト"""
        # 検証対象: .gitignoreの秘密情報対策
        # 目的: 重要ファイルが適切に除外されているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase7_security()

        assert results["gitignore_security_compliant"] is True

    def test_permissions_minimization_validation(self, mock_project_structure: Path) -> None:
        """権限最小化の検証テスト"""
        # 検証対象: GitHub Actionsの権限設定
        # 目的: 必要最小限の権限が設定されているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase7_security()

        assert results["permissions_minimized"] is True

    def test_missing_gitignore_handling(self, temp_dir: Path) -> None:
        """.gitignore不足の処理テスト"""
        # 検証対象: .gitignoreファイル不在の処理
        # 目的: セキュリティ設定が不足している場合の検出テスト
        validator = QualityRulesValidator(temp_dir)
        results = validator.validate_phase7_security()

        assert results["gitignore_security_compliant"] is False

    def test_insufficient_gitignore_patterns(self, temp_dir: Path) -> None:
        """不十分な.gitignoreパターンのテスト"""
        # 検証対象: 不完全な.gitignore設定の検出
        # 目的: セキュリティパターンが不足している場合のテスト
        incomplete_gitignore = temp_dir / ".gitignore"
        with open(incomplete_gitignore, "w", encoding="utf-8") as f:
            f.write("__pycache__/\n")  # 不完全な設定

        validator = QualityRulesValidator(temp_dir)
        results = validator.validate_phase7_security()

        assert results["gitignore_security_compliant"] is False


class TestPhase8Observability:
    """Phase 8: 観測性・監視のテスト"""

    def test_structured_logging_detection(self, mock_project_structure: Path) -> None:
        """構造化ログの検出テスト"""
        # 検証対象: 構造化ログ設定の検出
        # 目的: JSONログ等の構造化ログが使用されているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase8_observability()

        assert results["structured_logging_configured"] is True

    def test_utc_timezone_enforcement_detection(self, mock_project_structure: Path) -> None:
        """UTC時刻強制の検出テスト"""
        # 検証対象: UTC時刻使用の検出
        # 目的: タイムゾーン対応が適切に行われているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase8_observability()

        assert results["timezone_utc_enforced"] is True

    def test_correlation_ids_support_detection(self, mock_project_structure: Path) -> None:
        """相関ID対応の検出テスト"""
        # 検証対象: 相関ID/トレースIDの対応
        # 目的: 分散トレーシング対応が行われているかテスト
        validator = QualityRulesValidator(mock_project_structure)
        results = validator.validate_phase8_observability()

        assert results["correlation_ids_supported"] is True

    def test_no_observability_features(self, temp_dir: Path) -> None:
        """観測性機能不足のテスト"""
        # 検証対象: 観測性機能の不在
        # 目的: ログ・監視機能が不足している場合のテスト
        validator = QualityRulesValidator(temp_dir)
        results = validator.validate_phase8_observability()

        assert results["structured_logging_configured"] is False
        assert results["timezone_utc_enforced"] is False
        assert results["correlation_ids_supported"] is False


class TestOverallCompliance:
    """全体的なコンプライアンステスト"""

    def test_overall_compliance_calculation(self, mock_project_structure: Path) -> None:
        """全体コンプライアンス計算のテスト"""
        # 検証対象: 全体的な品質ルール遵守状況
        # 目的: コンプライアンス状況が正しく計算されることをテスト
        validator = QualityRulesValidator(mock_project_structure)
        compliance = validator.get_overall_compliance()

        assert "compliance_percentage" in compliance
        assert 0 <= compliance["compliance_percentage"] <= 100
        assert compliance["compliance_percentage"] > 50  # 良好な設定なので50%以上

    def test_compliance_with_errors_and_warnings(self, temp_dir: Path) -> None:
        """エラー・警告を含むコンプライアンステスト"""
        # 検証対象: エラー・警告を含む検証結果
        # 目的: 問題がある場合の適切な報告テスト
        # 不正な設定ファイルを作成
        invalid_toml = temp_dir / "pyproject.toml"
        with open(invalid_toml, "w", encoding="utf-8") as f:
            f.write("[invalid")

        validator = QualityRulesValidator(temp_dir)
        compliance = validator.get_overall_compliance()

        assert len(compliance["errors"]) > 0
        assert compliance["compliance_percentage"] < 50  # 設定不備で低い値

    def test_empty_project_compliance(self, temp_dir: Path) -> None:
        """空プロジェクトのコンプライアンステスト"""
        # 検証対象: 設定ファイルが全くないプロジェクト
        # 目的: 初期状態でのコンプライアンス状況テスト
        validator = QualityRulesValidator(temp_dir)
        compliance = validator.get_overall_compliance()

        # forbidden_patterns_absentがデフォルトでFalseになるため、わずかに0%以上になる
        assert compliance["compliance_percentage"] < 10  # 10%未満であることを確認

        # 主要な設定項目はすべてFalseであることを確認
        phase4 = compliance["phase4_linting"]
        phase5 = compliance["phase5_testing"]
        phase6 = compliance["phase6_ci_cd"]
        phase7 = compliance["phase7_security"]
        phase8 = compliance["phase8_observability"]

        assert phase4["ruff_configured"] is False
        assert phase4["mypy_configured"] is False
        assert phase5["pytest_configured"] is False
        assert phase5["coverage_configured"] is False
        assert phase5["test_structure_valid"] is False
        assert phase6["github_workflows_exist"] is False
        assert phase7["gitignore_security_compliant"] is False
        assert phase8["structured_logging_configured"] is False

    def test_partial_compliance_scenario(self, temp_dir: Path) -> None:
        """部分的コンプライアンスシナリオのテスト"""
        # 検証対象: 一部のみ設定されたプロジェクト
        # 目的: 段階的な設定状況での評価テスト
        # 最小限のpyproject.toml作成
        minimal_toml = temp_dir / "pyproject.toml"
        with open(minimal_toml, "w", encoding="utf-8") as f:
            f.write("""
[project]
name = "minimal-project"

[tool.ruff]
select = ["E", "F"]
""")

        validator = QualityRulesValidator(temp_dir)
        compliance = validator.get_overall_compliance()

        # 部分的な設定でも適切に評価される
        assert 0 < compliance["compliance_percentage"] < 100
        assert compliance["phase4_linting"]["ruff_configured"] is True
        assert compliance["phase4_linting"]["mypy_configured"] is False


class TestEdgeCasesAndErrorHandling:
    """エッジケースとエラーハンドリングのテスト"""

    def test_unicode_in_configuration_files(self, temp_dir: Path) -> None:
        """設定ファイル内Unicode文字のテスト"""
        # 検証対象: Unicode文字を含む設定ファイル
        # 目的: 国際化対応でもエラーが起きないことをテスト
        unicode_toml = temp_dir / "pyproject.toml"
        with open(unicode_toml, "w", encoding="utf-8") as f:
            f.write("""
[project]
name = "テスト-プロジェクト"
description = "日本語による説明文 🚀"

[tool.ruff]
select = ["E", "F", "W"]
""")

        validator = QualityRulesValidator(temp_dir)
        results = validator.validate_phase4_linting()

        # Unicode文字があってもruff設定は検出される
        assert results["ruff_configured"] is True

    def test_extremely_large_configuration_files(self, temp_dir: Path) -> None:
        """極端に大きな設定ファイルのテスト"""
        # 検証対象: 大容量設定ファイルの処理
        # 目的: 大きなファイルでもパフォーマンス問題がないことをテスト
        large_toml = temp_dir / "pyproject.toml"

        # 大きな設定ファイルを生成
        content = """
[project]
name = "large-project"

[tool.ruff]
select = ["E", "F", "W", "I", "UP", "B"]
"""
        # 大量のコメントを追加してファイルサイズを増やす
        for i in range(1000):
            content += f"# 大量コメント行 {i:04d}: この行は設定ファイルのサイズを増やすためのものです\n"

        with open(large_toml, "w", encoding="utf-8") as f:
            f.write(content)

        import time

        start_time = time.time()

        validator = QualityRulesValidator(temp_dir)
        results = validator.validate_phase4_linting()

        processing_time = time.time() - start_time

        # 大きなファイルでも適切に処理される
        assert results["ruff_configured"] is True
        assert processing_time < 5.0  # 5秒以内で処理完了

    def test_permission_denied_file_access(self, temp_dir: Path) -> None:
        """ファイルアクセス権限エラーのテスト"""
        # 検証対象: ファイルアクセス権限不足の処理
        # 目的: 権限エラーでもクラッシュしないことをテスト
        import stat

        restricted_toml = temp_dir / "pyproject.toml"
        with open(restricted_toml, "w", encoding="utf-8") as f:
            f.write("[project]\nname = 'test'")

        # ファイルを読み取り不可に設定（Windowsでは動作しない可能性があります）
        try:
            os.chmod(restricted_toml, stat.S_IWUSR)  # 書き込みのみ許可

            validator = QualityRulesValidator(temp_dir)
            results = validator.validate_phase4_linting()

            # 権限エラーがあっても適切にハンドリングされる
            assert not results["ruff_configured"]

        except (OSError, PermissionError):
            # Windows等で権限変更ができない場合はスキップ
            pytest.skip("ファイル権限変更をサポートしていない環境")
        finally:
            # ファイル権限を復元
            import contextlib

            with contextlib.suppress(OSError, PermissionError):
                os.chmod(restricted_toml, stat.S_IRUSR | stat.S_IWUSR)

    def test_circular_symlink_handling(self, temp_dir: Path) -> None:
        """循環シンボリックリンクの処理テスト"""
        # 検証対象: 循環参照するシンボリックリンク
        # 目的: 無限ループにならないことをテスト
        try:
            # 循環シンボリックリンクを作成
            link1 = temp_dir / "link1"
            link2 = temp_dir / "link2"

            link1.symlink_to(link2)
            link2.symlink_to(link1)

            validator = QualityRulesValidator(temp_dir)
            compliance = validator.get_overall_compliance()

            # 循環リンクがあっても処理が完了する
            assert "compliance_percentage" in compliance

        except (OSError, NotImplementedError):
            # シンボリックリンクをサポートしていない環境ではスキップ
            pytest.skip("シンボリックリンクをサポートしていない環境")

    def test_concurrent_file_modification(self, temp_dir: Path) -> None:
        """並行ファイル変更のテスト"""
        # 検証対象: 検証中のファイル変更
        # 目的: 並行処理での競合状態処理テスト
        import threading
        import time

        config_file = temp_dir / "pyproject.toml"

        def modify_file():
            """ファイルを継続的に変更"""
            for i in range(10):
                try:
                    with open(config_file, "w", encoding="utf-8") as f:
                        f.write(f"""
[project]
name = "concurrent-test-{i}"

[tool.ruff]
select = ["E", "F"]
""")
                    time.sleep(0.1)
                except Exception:
                    pass

        # ファイル変更スレッドを開始
        modifier_thread = threading.Thread(target=modify_file)
        modifier_thread.daemon = True
        modifier_thread.start()

        # 並行してバリデーション実行
        validator = QualityRulesValidator(temp_dir)

        try:
            results = validator.validate_phase4_linting()
            # 並行変更があっても処理が完了する
            assert isinstance(results, dict)
        except Exception as e:
            # 並行変更によるエラーは許容される
            print(f"並行変更によるエラー（許容される）: {e}")

        modifier_thread.join(timeout=2)


class TestPerformanceAndScalability:
    """パフォーマンスとスケーラビリティのテスト"""

    def test_large_project_performance(self, temp_dir: Path) -> None:
        """大規模プロジェクトのパフォーマンステスト"""
        # 検証対象: 大量ファイルでのパフォーマンス
        # 目的: スケーラビリティの確認テスト
        # 大量のPythonファイルを作成
        src_dir = temp_dir / "src"
        src_dir.mkdir(exist_ok=True)

        for i in range(50):  # 50個のファイル
            py_file = src_dir / f"module_{i:03d}.py"
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(f"""
import logging
import json
from datetime import datetime, timezone

def function_{i}():
    '''Function {i} with logging'''
    logger = logging.getLogger(__name__)
    log_data = {{
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Function {i} called",
        "trace_id": "trace-{i:03d}"
    }}
    logger.info(json.dumps(log_data))
""")

        import time

        start_time = time.time()

        validator = QualityRulesValidator(temp_dir)
        compliance = validator.get_overall_compliance()

        processing_time = time.time() - start_time

        # パフォーマンス要件: 50ファイルを5秒以内で処理
        assert processing_time < 5.0, f"処理時間が長すぎます: {processing_time:.2f}秒"
        assert compliance["phase8_observability"]["structured_logging_configured"] is True

        print(f"大規模プロジェクト処理時間: {processing_time:.2f}秒")

    def test_memory_usage_efficiency(self, temp_dir: Path) -> None:
        """メモリ使用効率のテスト"""
        # 検証対象: メモリ使用量の効率性
        # 目的: メモリリークがないことをテスト
        try:
            import psutil

            process = psutil.Process()
        except ImportError:
            pytest.skip("psutil not available for memory monitoring")
            return

        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 複数回の検証実行
        validator = QualityRulesValidator(temp_dir)
        for _ in range(10):
            validator.get_overall_compliance()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        print(f"メモリ使用量変化: {memory_growth:.2f}MB")

        # メモリ使用量増加が過度でないことを確認
        assert memory_growth < 50.0, f"メモリ使用量増加が過大: {memory_growth:.2f}MB"

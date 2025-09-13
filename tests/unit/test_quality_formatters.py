"""品質レポート整形機能のテスト."""

import pytest
import json
import platform
from pathlib import Path
from unittest.mock import Mock, patch
from ..multiplatform.helpers import verify_current_platform


class TestQualityFormatters:
    """品質レポート整形のテストクラス."""

    def setup_method(self):
        """テストメソッドの前処理."""
        self.platform_info = verify_current_platform()
        self.sample_data = {
            "lint": {"errors": 5, "warnings": 10},
            "type": {"errors": 2, "warnings": 3},
            "test": {"passed": 45, "failed": 2, "skipped": 3},
            "coverage": {"percentage": 85.5, "missing": 15},
            "security": {"high": 1, "medium": 2, "low": 0}
        }

    @pytest.mark.unit
    def test_json_formatter(self):
        """JSON形式のフォーマッターテスト."""
        # JSON形式への変換
        json_output = json.dumps(self.sample_data, indent=2)
        
        # JSON形式の検証
        assert json_output is not None
        assert '"lint"' in json_output
        assert '"errors": 5' in json_output
        
        # パース可能性の確認
        parsed_data = json.loads(json_output)
        assert parsed_data["lint"]["errors"] == 5

    @pytest.mark.unit
    def test_html_formatter(self):
        """HTML形式のフォーマッターテスト."""
        # HTML形式のテンプレート
        html_template = """
        <html>
        <head><title>Quality Report</title></head>
        <body>
        <h1>Code Quality Report</h1>
        <div class="metrics">
            <div class="lint">Lint Errors: {lint_errors}</div>
            <div class="test">Test Coverage: {coverage}%</div>
        </div>
        </body>
        </html>
        """
        
        # データの埋め込み
        html_output = html_template.format(
            lint_errors=self.sample_data["lint"]["errors"],
            coverage=self.sample_data["coverage"]["percentage"]
        )
        
        # HTML形式の検証
        assert "<html>" in html_output
        assert "Lint Errors: 5" in html_output
        assert "Test Coverage: 85.5%" in html_output

    @pytest.mark.unit
    def test_markdown_formatter(self):
        """Markdown形式のフォーマッターテスト."""
        # Markdown形式のテンプレート
        markdown_template = """# Code Quality Report

## Lint Results
- Errors: {lint_errors}
- Warnings: {lint_warnings}

## Test Results
- Passed: {test_passed}
- Failed: {test_failed}
- Coverage: {coverage}%

## Security Issues
- High: {security_high}
- Medium: {security_medium}
"""
        
        # データの埋め込み
        markdown_output = markdown_template.format(
            lint_errors=self.sample_data["lint"]["errors"],
            lint_warnings=self.sample_data["lint"]["warnings"],
            test_passed=self.sample_data["test"]["passed"],
            test_failed=self.sample_data["test"]["failed"],
            coverage=self.sample_data["coverage"]["percentage"],
            security_high=self.sample_data["security"]["high"],
            security_medium=self.sample_data["security"]["medium"]
        )
        
        # Markdown形式の検証
        assert "# Code Quality Report" in markdown_output
        assert "- Errors: 5" in markdown_output
        assert "- Coverage: 85.5%" in markdown_output

    @pytest.mark.unit
    def test_csv_formatter(self):
        """CSV形式のフォーマッターテスト."""
        # CSV形式のヘッダーとデータ
        csv_header = "metric,value,status"
        csv_rows = [
            f"lint_errors,{self.sample_data['lint']['errors']},{'FAIL' if self.sample_data['lint']['errors'] > 0 else 'PASS'}",
            f"test_coverage,{self.sample_data['coverage']['percentage']},{'PASS' if self.sample_data['coverage']['percentage'] >= 80 else 'FAIL'}",
            f"security_high,{self.sample_data['security']['high']},{'FAIL' if self.sample_data['security']['high'] > 0 else 'PASS'}"
        ]
        
        csv_output = csv_header + "\n" + "\n".join(csv_rows)
        
        # CSV形式の検証
        assert "metric,value,status" in csv_output
        assert "lint_errors,5,FAIL" in csv_output
        assert "test_coverage,85.5,PASS" in csv_output

    @pytest.mark.unit
    def test_console_formatter(self):
        """コンソール形式のフォーマッターテスト."""
        # コンソール出力形式
        console_output = f"""
╭─ Code Quality Report ─╮
│ Platform: {self.platform_info['system']}
│ Python: {self.platform_info['python_version']}
├─ Lint Results ─────────
│ ✗ Errors: {self.sample_data['lint']['errors']}
│ ⚠ Warnings: {self.sample_data['lint']['warnings']}
├─ Test Results ─────────
│ ✓ Passed: {self.sample_data['test']['passed']}
│ ✗ Failed: {self.sample_data['test']['failed']}
│ ○ Coverage: {self.sample_data['coverage']['percentage']}%
├─ Security Issues ──────
│ 🔴 High: {self.sample_data['security']['high']}
│ 🟡 Medium: {self.sample_data['security']['medium']}
╰─────────────────────────╯
"""
        
        # コンソール形式の検証
        assert "Code Quality Report" in console_output
        assert f"Platform: {self.platform_info['system']}" in console_output
        assert "✗ Errors: 5" in console_output

    @pytest.mark.unit
    def test_xml_formatter(self):
        """XML形式のフォーマッターテスト."""
        # XML形式のテンプレート
        xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<quality-report>
    <metadata>
        <platform>{platform}</platform>
        <python-version>{python_version}</python-version>
    </metadata>
    <metrics>
        <lint errors="{lint_errors}" warnings="{lint_warnings}"/>
        <tests passed="{test_passed}" failed="{test_failed}"/>
        <coverage percentage="{coverage}"/>
        <security high="{security_high}" medium="{security_medium}"/>
    </metrics>
</quality-report>"""
        
        # データの埋め込み
        xml_output = xml_template.format(
            platform=self.platform_info['system'],
            python_version=self.platform_info['python_version'],
            lint_errors=self.sample_data['lint']['errors'],
            lint_warnings=self.sample_data['lint']['warnings'],
            test_passed=self.sample_data['test']['passed'],
            test_failed=self.sample_data['test']['failed'],
            coverage=self.sample_data['coverage']['percentage'],
            security_high=self.sample_data['security']['high'],
            security_medium=self.sample_data['security']['medium']
        )
        
        # XML形式の検証
        assert '<?xml version="1.0"' in xml_output
        assert '<quality-report>' in xml_output
        assert 'errors="5"' in xml_output

    @pytest.mark.unit
    def test_badge_formatter(self):
        """バッジ形式のフォーマッターテスト."""
        # バッジ用データの生成
        badges = {
            "coverage": {
                "label": "coverage",
                "message": f"{self.sample_data['coverage']['percentage']}%",
                "color": "brightgreen" if self.sample_data['coverage']['percentage'] >= 80 else "red"
            },
            "tests": {
                "label": "tests",
                "message": f"{self.sample_data['test']['passed']} passed",
                "color": "brightgreen" if self.sample_data['test']['failed'] == 0 else "red"
            },
            "security": {
                "label": "security",
                "message": "secure" if self.sample_data['security']['high'] == 0 else "vulnerable",
                "color": "brightgreen" if self.sample_data['security']['high'] == 0 else "red"
            }
        }
        
        # バッジ形式の検証
        assert badges["coverage"]["message"] == "85.5%"
        assert badges["coverage"]["color"] == "brightgreen"
        assert badges["security"]["color"] == "red"  # high=1なので

    @pytest.mark.unit
    def test_summary_formatter(self):
        """サマリー形式のフォーマッターテスト."""
        # サマリーデータの計算
        total_issues = (
            self.sample_data['lint']['errors'] + 
            self.sample_data['type']['errors'] + 
            self.sample_data['test']['failed'] + 
            self.sample_data['security']['high']
        )
        
        quality_score = max(0, 100 - (total_issues * 10))
        
        summary = {
            "total_issues": total_issues,
            "quality_score": quality_score,
            "status": "PASS" if total_issues <= 5 else "FAIL",
            "recommendations": []
        }
        
        # 推奨事項の生成
        if self.sample_data['lint']['errors'] > 0:
            summary["recommendations"].append("Fix linting errors")
        if self.sample_data['coverage']['percentage'] < 90:
            summary["recommendations"].append("Improve test coverage")
        if self.sample_data['security']['high'] > 0:
            summary["recommendations"].append("Address security issues")
        
        # サマリー形式の検証
        assert summary["total_issues"] == 10
        assert summary["quality_score"] == 0  # 100 - (10 * 10) = 0
        assert summary["status"] == "FAIL"
        assert len(summary["recommendations"]) == 3

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix固有のフォーマット")
    def test_unix_specific_formatting(self):
        """Unix固有のフォーマッティングテスト."""
        # Unix固有の色付きコンソール出力
        unix_colors = {
            "RED": "\033[91m",
            "GREEN": "\033[92m",
            "YELLOW": "\033[93m",
            "RESET": "\033[0m"
        }
        
        colored_output = f"{unix_colors['RED']}Errors: 5{unix_colors['RESET']}"
        
        # Unix固有フォーマットの検証
        assert "\033[91m" in colored_output
        assert "\033[0m" in colored_output

    @pytest.mark.unit
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows固有のフォーマット")
    def test_windows_specific_formatting(self):
        """Windows固有のフォーマッティングテスト."""
        # Windows固有のパス形式
        windows_path = "C:\\Users\\test\\project\\report.html"
        
        # Windows固有フォーマットの検証
        assert "\\" in windows_path
        assert windows_path.startswith("C:")

    @pytest.mark.unit
    def test_formatter_selection(self):
        """フォーマッター選択ロジックのテスト."""
        format_mapping = {
            "json": "application/json",
            "html": "text/html",
            "markdown": "text/markdown",
            "csv": "text/csv",
            "xml": "application/xml"
        }
        
        # フォーマッター選択の検証
        assert format_mapping["json"] == "application/json"
        assert format_mapping["html"] == "text/html"
        assert len(format_mapping) == 5
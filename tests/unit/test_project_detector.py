"""ProjectDetectorのテスト"""

import pytest

from setup_repo.project_detector import ProjectDetector


@pytest.mark.unit
class TestProjectDetector:
    """ProjectDetectorクラスのテスト"""

    def test_detect_python_project(self, temp_dir):
        """Pythonプロジェクト検出テスト"""
        # Pythonプロジェクトファイルを作成
        (temp_dir / "pyproject.toml").write_text("[build-system]")
        (temp_dir / "main.py").write_text("print('hello')")

        detector = ProjectDetector(temp_dir)
        project_types = detector.detect_project_types()

        assert "python" in project_types

    def test_detect_node_project(self, temp_dir):
        """Node.jsプロジェクト検出テスト"""
        # Node.jsプロジェクトファイルを作成
        (temp_dir / "package.json").write_text('{"name": "test"}')
        (temp_dir / "index.js").write_text("console.log('hello')")

        detector = ProjectDetector(temp_dir)
        project_types = detector.detect_project_types()

        assert "node" in project_types

    def test_detect_multiple_project_types(self, temp_dir):
        """複数プロジェクトタイプ検出テスト"""
        # Python + Node.js プロジェクト
        (temp_dir / "pyproject.toml").write_text("[build-system]")
        (temp_dir / "package.json").write_text('{"name": "test"}')

        detector = ProjectDetector(temp_dir)
        project_types = detector.detect_project_types()

        assert "python" in project_types
        assert "node" in project_types

    def test_detect_tools(self, temp_dir):
        """ツール検出テスト"""
        # uvとVS Codeファイルを作成
        (temp_dir / "uv.lock").write_text("# uv lock file")
        vscode_dir = temp_dir / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "settings.json").write_text("{}")

        detector = ProjectDetector(temp_dir)
        tools = detector.detect_tools()

        assert "uv" in tools
        assert "vscode" in tools

    def test_get_recommended_templates_python(self, temp_dir):
        """Python推奨テンプレート取得テスト"""
        # Pythonプロジェクト + uv + VS Code
        (temp_dir / "pyproject.toml").write_text("[build-system]")
        (temp_dir / "uv.lock").write_text("# uv lock file")
        vscode_dir = temp_dir / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "settings.json").write_text("{}")

        detector = ProjectDetector(temp_dir)
        templates = detector.get_recommended_templates()

        assert "common" in templates
        assert "python" in templates
        assert "uv" in templates
        assert "vscode" in templates

    def test_get_recommended_templates_node(self, temp_dir):
        """Node.js推奨テンプレート取得テスト"""
        # Node.jsプロジェクト
        (temp_dir / "package.json").write_text('{"name": "test"}')

        detector = ProjectDetector(temp_dir)
        templates = detector.get_recommended_templates()

        assert "common" in templates
        assert "node" in templates

    def test_analyze_project(self, temp_dir):
        """プロジェクト分析テスト"""
        # 複合プロジェクト
        (temp_dir / "pyproject.toml").write_text("[build-system]")
        (temp_dir / "uv.lock").write_text("# uv lock file")

        detector = ProjectDetector(temp_dir)
        analysis = detector.analyze_project()

        assert "python" in analysis["project_types"]
        assert "uv" in analysis["tools"]
        assert "common" in analysis["recommended_templates"]
        assert "python" in analysis["recommended_templates"]
        assert "uv" in analysis["recommended_templates"]

    def test_empty_project(self, temp_dir):
        """空プロジェクト検出テスト"""
        detector = ProjectDetector(temp_dir)

        project_types = detector.detect_project_types()
        tools = detector.detect_tools()
        templates = detector.get_recommended_templates()

        assert len(project_types) == 0
        assert len(tools) == 0
        assert templates == ["common"]  # 常にcommonは含まれる

    def test_rust_project_detection(self, temp_dir):
        """Rustプロジェクト検出テスト"""
        (temp_dir / "Cargo.toml").write_text('[package]\nname = "test"')
        src_dir = temp_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.rs").write_text('fn main() { println!("Hello"); }')

        detector = ProjectDetector(temp_dir)
        project_types = detector.detect_project_types()

        assert "rust" in project_types

    def test_go_project_detection(self, temp_dir):
        """Goプロジェクト検出テスト"""
        (temp_dir / "go.mod").write_text("module test")
        (temp_dir / "main.go").write_text("package main")

        detector = ProjectDetector(temp_dir)
        project_types = detector.detect_project_types()

        assert "go" in project_types

"""プロジェクト検出機能のテスト"""

from pathlib import Path

import pytest

from src.setup_repo.project_detector import ProjectDetector

from ..multiplatform.helpers import verify_current_platform


class TestProjectDetector:
    """ProjectDetectorのテストクラス"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """テスト用プロジェクトディレクトリ"""
        return tmp_path / "test_project"

    @pytest.fixture
    def project_detector(self, temp_project):
        """ProjectDetectorインスタンス"""
        temp_project.mkdir(parents=True, exist_ok=True)
        return ProjectDetector(temp_project)

    @pytest.mark.unit
    def test_init(self, temp_project):
        """初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        detector = ProjectDetector(temp_project)
        assert detector.repo_path == Path(temp_project)

    @pytest.mark.unit
    def test_detect_project_types_empty(self, project_detector):
        """空のプロジェクトでのタイプ検出"""
        verify_current_platform()  # プラットフォーム検証

        project_types = project_detector.detect_project_types()
        assert project_types == set()

    @pytest.mark.unit
    def test_detect_project_types_python_pyproject(self, project_detector):
        """Pythonプロジェクト検出（pyproject.toml）"""
        verify_current_platform()  # プラットフォーム検証

        # pyproject.tomlを作成
        (project_detector.repo_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")

        project_types = project_detector.detect_project_types()
        assert "python" in project_types

    @pytest.mark.unit
    def test_detect_project_types_python_setup_py(self, project_detector):
        """Pythonプロジェクト検出（setup.py）"""
        verify_current_platform()  # プラットフォーム検証

        # setup.pyを作成
        (project_detector.repo_path / "setup.py").write_text("from setuptools import setup", encoding="utf-8")

        project_types = project_detector.detect_project_types()
        assert "python" in project_types

    @pytest.mark.unit
    def test_detect_project_types_python_by_extension(self, project_detector):
        """Pythonプロジェクト検出（拡張子）"""
        verify_current_platform()  # プラットフォーム検証

        # .pyファイルを作成
        (project_detector.repo_path / "main.py").write_text("print('hello')", encoding="utf-8")

        project_types = project_detector.detect_project_types()
        assert "python" in project_types

    @pytest.mark.unit
    def test_detect_project_types_python_by_directory(self, project_detector):
        """Pythonプロジェクト検出（ディレクトリ）"""
        verify_current_platform()  # プラットフォーム検証

        # srcディレクトリを作成
        (project_detector.repo_path / "src").mkdir()

        project_types = project_detector.detect_project_types()
        assert "python" in project_types

    @pytest.mark.unit
    def test_detect_project_types_node(self, project_detector):
        """Node.jsプロジェクト検出"""
        verify_current_platform()  # プラットフォーム検証

        # package.jsonを作成
        (project_detector.repo_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")

        project_types = project_detector.detect_project_types()
        assert "node" in project_types

    @pytest.mark.unit
    def test_detect_project_types_rust(self, project_detector):
        """Rustプロジェクト検出"""
        verify_current_platform()  # プラットフォーム検証

        # Cargo.tomlを作成
        (project_detector.repo_path / "Cargo.toml").write_text('[package]\nname = "test"', encoding="utf-8")

        project_types = project_detector.detect_project_types()
        assert "rust" in project_types

    @pytest.mark.unit
    def test_detect_project_types_go(self, project_detector):
        """Goプロジェクト検出"""
        verify_current_platform()  # プラットフォーム検証

        # go.modを作成
        (project_detector.repo_path / "go.mod").write_text("module test", encoding="utf-8")

        project_types = project_detector.detect_project_types()
        assert "go" in project_types

    @pytest.mark.unit
    def test_detect_project_types_java(self, project_detector):
        """Javaプロジェクト検出"""
        verify_current_platform()  # プラットフォーム検証

        # pom.xmlを作成
        (project_detector.repo_path / "pom.xml").write_text("<project></project>", encoding="utf-8")

        project_types = project_detector.detect_project_types()
        assert "java" in project_types

    @pytest.mark.unit
    def test_detect_project_types_csharp(self, project_detector):
        """C#プロジェクト検出"""
        verify_current_platform()  # プラットフォーム検証

        # .csprojファイルを作成
        (project_detector.repo_path / "test.csproj").write_text("<Project></Project>", encoding="utf-8")

        project_types = project_detector.detect_project_types()
        assert "csharp" in project_types

    @pytest.mark.unit
    def test_detect_project_types_multiple(self, project_detector):
        """複数プロジェクトタイプの検出"""
        verify_current_platform()  # プラットフォーム検証

        # PythonとNode.jsの両方の特徴を持つプロジェクト
        (project_detector.repo_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        (project_detector.repo_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")

        project_types = project_detector.detect_project_types()
        assert "python" in project_types
        assert "node" in project_types

    @pytest.mark.unit
    def test_detect_tools_empty(self, project_detector):
        """空のプロジェクトでのツール検出"""
        verify_current_platform()  # プラットフォーム検証

        tools = project_detector.detect_tools()
        assert tools == set()

    @pytest.mark.unit
    def test_detect_tools_uv(self, project_detector):
        """uvツール検出"""
        verify_current_platform()  # プラットフォーム検証

        # uv.lockを作成
        (project_detector.repo_path / "uv.lock").write_text("# uv lock file", encoding="utf-8")

        tools = project_detector.detect_tools()
        assert "uv" in tools

    @pytest.mark.unit
    def test_detect_tools_vscode(self, project_detector):
        """VS Codeツール検出"""
        verify_current_platform()  # プラットフォーム検証

        # .vscodeディレクトリとsettings.jsonを作成
        vscode_dir = project_detector.repo_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "settings.json").write_text("{}", encoding="utf-8")

        tools = project_detector.detect_tools()
        assert "vscode" in tools

    @pytest.mark.unit
    def test_detect_tools_docker(self, project_detector):
        """Dockerツール検出"""
        verify_current_platform()  # プラットフォーム検証

        # Dockerfileを作成
        (project_detector.repo_path / "Dockerfile").write_text("FROM python:3.9", encoding="utf-8")

        tools = project_detector.detect_tools()
        assert "docker" in tools

    @pytest.mark.unit
    def test_detect_tools_git(self, project_detector):
        """Gitツール検出"""
        verify_current_platform()  # プラットフォーム検証

        # .gitディレクトリを作成
        (project_detector.repo_path / ".git").mkdir()

        tools = project_detector.detect_tools()
        assert "git" in tools

    @pytest.mark.unit
    def test_detect_tools_multiple(self, project_detector):
        """複数ツールの検出"""
        verify_current_platform()  # プラットフォーム検証

        # 複数のツールの特徴を作成
        (project_detector.repo_path / "uv.lock").write_text("# uv lock", encoding="utf-8")
        (project_detector.repo_path / ".gitignore").write_text("*.pyc", encoding="utf-8")

        tools = project_detector.detect_tools()
        assert "uv" in tools
        assert "git" in tools

    @pytest.mark.unit
    def test_get_recommended_templates_empty(self, project_detector):
        """空のプロジェクトでの推奨テンプレート"""
        verify_current_platform()  # プラットフォーム検証

        templates = project_detector.get_recommended_templates()
        assert templates == ["common"]

    @pytest.mark.unit
    def test_get_recommended_templates_python(self, project_detector):
        """Pythonプロジェクトでの推奨テンプレート"""
        verify_current_platform()  # プラットフォーム検証

        # Pythonプロジェクトの特徴を作成
        (project_detector.repo_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        (project_detector.repo_path / "uv.lock").write_text("# uv lock", encoding="utf-8")

        templates = project_detector.get_recommended_templates()
        assert "common" in templates
        assert "python" in templates
        assert "uv" in templates

    @pytest.mark.unit
    def test_get_recommended_templates_deduplication(self, project_detector):
        """推奨テンプレートの重複除去"""
        verify_current_platform()  # プラットフォーム検証

        # 同じテンプレートが複数回推奨される状況を作成
        # （実際には発生しないが、重複除去のテスト）
        templates = project_detector.get_recommended_templates()

        # 重複がないことを確認
        assert len(templates) == len(set(templates))

    @pytest.mark.unit
    def test_path_exists_security(self, project_detector):
        """パス存在確認のセキュリティテスト"""
        verify_current_platform()  # プラットフォーム検証

        # パストラバーサル攻撃の試行
        assert project_detector._path_exists("../../../etc/passwd") is False
        assert project_detector._path_exists("/etc/passwd") is False
        assert project_detector._path_exists("..\\..\\windows\\system32") is False

    @pytest.mark.unit
    def test_path_exists_valid_paths(self, project_detector):
        """有効なパスでの存在確認"""
        verify_current_platform()  # プラットフォーム検証

        # 存在しないファイル
        assert project_detector._path_exists("nonexistent.txt") is False

        # 存在するファイルを作成してテスト
        test_file = project_detector.repo_path / "test.txt"
        test_file.write_text("test", encoding="utf-8")
        assert project_detector._path_exists("test.txt") is True

    @pytest.mark.unit
    def test_has_files_with_extensions(self, project_detector):
        """拡張子によるファイル検索"""
        verify_current_platform()  # プラットフォーム検証

        # .pyファイルが存在しない場合
        assert project_detector._has_files_with_extensions([".py"]) is False

        # .pyファイルを作成
        (project_detector.repo_path / "main.py").write_text("print('hello')", encoding="utf-8")
        assert project_detector._has_files_with_extensions([".py"]) is True

        # サブディレクトリ内のファイルも検出
        subdir = project_detector.repo_path / "subdir"
        subdir.mkdir()
        (subdir / "module.py").write_text("# module", encoding="utf-8")
        assert project_detector._has_files_with_extensions([".py"]) is True

    @pytest.mark.unit
    def test_has_files_with_extensions_multiple(self, project_detector):
        """複数拡張子でのファイル検索"""
        verify_current_platform()  # プラットフォーム検証

        # .jsファイルを作成
        (project_detector.repo_path / "app.js").write_text("console.log('hello')", encoding="utf-8")

        # 複数の拡張子で検索
        assert project_detector._has_files_with_extensions([".py", ".js"]) is True
        assert project_detector._has_files_with_extensions([".py", ".ts"]) is False

    @pytest.mark.unit
    def test_analyze_project_comprehensive(self, project_detector):
        """包括的なプロジェクト分析"""
        verify_current_platform()  # プラットフォーム検証

        # 複合的なプロジェクト構造を作成
        (project_detector.repo_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        (project_detector.repo_path / "main.py").write_text("print('hello')", encoding="utf-8")
        (project_detector.repo_path / "uv.lock").write_text("# uv lock", encoding="utf-8")
        (project_detector.repo_path / ".gitignore").write_text("*.pyc", encoding="utf-8")

        vscode_dir = project_detector.repo_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "settings.json").write_text("{}", encoding="utf-8")

        analysis = project_detector.analyze_project()

        assert "python" in analysis["project_types"]
        assert "uv" in analysis["tools"]
        assert "git" in analysis["tools"]
        assert "vscode" in analysis["tools"]
        assert "common" in analysis["recommended_templates"]
        assert "python" in analysis["recommended_templates"]

    @pytest.mark.unit
    def test_check_project_type_logic(self, project_detector):
        """プロジェクトタイプチェックロジックのテスト"""
        verify_current_platform()  # プラットフォーム検証

        # Pythonのルールを取得
        python_rules = project_detector.DETECTION_RULES["python"]

        # ファイルが存在しない場合
        assert project_detector._check_project_type(python_rules) is False

        # pyproject.tomlを作成（ファイル存在による検出）
        (project_detector.repo_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        assert project_detector._check_project_type(python_rules) is True

    @pytest.mark.unit
    def test_detection_rules_completeness(self, project_detector):
        """検出ルールの完全性テスト"""
        verify_current_platform()  # プラットフォーム検証

        # すべてのプロジェクトタイプにルールが定義されていることを確認
        for project_type, rules in project_detector.DETECTION_RULES.items():
            assert isinstance(rules, dict)
            assert "files" in rules
            assert "extensions" in rules
            assert "directories" in rules
            assert isinstance(rules["files"], list)
            assert isinstance(rules["extensions"], list)
            assert isinstance(rules["directories"], list)

    @pytest.mark.unit
    def test_tool_detection_completeness(self, project_detector):
        """ツール検出の完全性テスト"""
        verify_current_platform()  # プラットフォーム検証

        # すべてのツールに検出ルールが定義されていることを確認
        for tool, indicators in project_detector.TOOL_DETECTION.items():
            assert isinstance(indicators, list)
            assert len(indicators) > 0
            for indicator in indicators:
                assert isinstance(indicator, str)
                assert len(indicator) > 0

    @pytest.mark.unit
    def test_edge_cases(self, project_detector):
        """エッジケースのテスト"""
        verify_current_platform()  # プラットフォーム検証

        # 空のファイル名での検出
        empty_rules = {"files": [""], "extensions": [], "directories": []}
        assert project_detector._check_project_type(empty_rules) is False

        # 存在しない拡張子での検索
        assert project_detector._has_files_with_extensions([".nonexistent"]) is False

        # 空の拡張子リストでの検索
        assert project_detector._has_files_with_extensions([]) is False

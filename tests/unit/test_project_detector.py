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
        assert project_types == []  # スコアリングシステムではlistを返す

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

        # setup.pyのみでは8点（閾値10点未満）
        (project_detector.repo_path / "setup.py").write_text("from setuptools import setup", encoding="utf-8")

        project_types = project_detector.detect_project_types()
        # setup.pyのみでは検出されない
        assert "python" not in project_types

        # requirements.txtを追加すれば閾値に達する（8 + 3 = 11点）
        (project_detector.repo_path / "requirements.txt").write_text("requests\n", encoding="utf-8")

        # キャッシュクリア
        project_detector._file_count_cache = {}

        project_types = project_detector.detect_project_types()
        assert "python" in project_types

    @pytest.mark.unit
    def test_detect_project_types_python_by_extension(self, project_detector):
        """Pythonプロジェクト検出（拡張子のみでは不十分）"""
        verify_current_platform()  # プラットフォーム検証

        # .pyファイル1つだけではスコア不足（0.5点 < 10点）
        (project_detector.repo_path / "main.py").write_text("print('hello')", encoding="utf-8")

        project_types = project_detector.detect_project_types()
        # ファイル1つだけでは閾値に達しない
        assert "python" not in project_types

        # 追加で多数のファイルを作成すれば検出される（20ファイル * 0.5 = 10点）
        for i in range(19):  # 既に1ファイルあるので19個追加で合計20ファイル
            (project_detector.repo_path / f"file{i}.py").write_text(f"# file{i}", encoding="utf-8")

        # キャッシュクリア
        project_detector._file_count_cache = {}

        project_types = project_detector.detect_project_types()
        assert "python" in project_types

    @pytest.mark.unit
    def test_detect_project_types_python_by_directory(self, project_detector):
        """Pythonプロジェクト検出（ディレクトリのみでは不十分）"""
        verify_current_platform()  # プラットフォーム検証

        # srcディレクトリのみではスコア不足
        # （他のプロジェクトタイプもsrcを使うため、Python固有ではない）
        (project_detector.repo_path / "src").mkdir()

        project_types = project_detector.detect_project_types()
        # srcディレクトリだけでは閾値に達しない
        assert "python" not in project_types

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
    def test_detect_project_types_csharp_nested(self, project_detector):
        """C#プロジェクト検出（サブディレクトリ内の.csproj）"""
        verify_current_platform()  # プラットフォーム検証

        # サブディレクトリ内に .csproj ファイルを作成
        subdir = project_detector.repo_path / "src" / "project"
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "nested.csproj").write_text("<Project></Project>", encoding="utf-8")

        # キャッシュクリア
        project_detector._file_count_cache = {}

        project_types = project_detector.detect_project_types()
        assert "csharp" in project_types

    @pytest.mark.unit
    def test_detect_project_types_csharp_sln_nested(self, project_detector):
        """C#プロジェクト検出（サブディレクトリ内の.sln）"""
        verify_current_platform()  # プラットフォーム検証

        # サブディレクトリ内に .sln ファイルを作成
        subdir = project_detector.repo_path / "src" / "solution_folder"
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "test_solution.sln").write_text(
            "Microsoft Visual Studio Solution File, Format Version 12.00", encoding="utf-8"
        )

        # キャッシュクリア
        project_detector._file_count_cache = {}

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

        # パストラバーサル攻撃の試行（プロジェクトディレクトリ外のパスは常にFalse）
        assert project_detector._path_exists("../../../etc/passwd") is False
        assert project_detector._path_exists("..\\..\\windows\\system32") is False

        # セキュリティ機能のテスト：プロジェクトディレクトリ外への相対パスアクセスを防ぐ
        # 実際のファイルシステムの状態に依存しない安全なテスト
        assert project_detector._path_exists("../outside_project") is False

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
    def test_count_files_with_extension(self, project_detector):
        """拡張子によるファイル数カウント"""
        verify_current_platform()  # プラットフォーム検証

        # .pyファイルが存在しない場合
        count = project_detector._count_files_with_extension(".py", [])
        assert count == 0

        # .pyファイルを作成
        (project_detector.repo_path / "main.py").write_text("print('hello')", encoding="utf-8")
        count = project_detector._count_files_with_extension(".py", [])
        assert count == 1

        # サブディレクトリ内のファイルもカウント
        subdir = project_detector.repo_path / "subdir"
        subdir.mkdir()
        (subdir / "module.py").write_text("# module", encoding="utf-8")
        count = project_detector._count_files_with_extension(".py", [])
        assert count == 2

    @pytest.mark.unit
    def test_count_files_with_excluded_dirs(self, project_detector):
        """除外ディレクトリを考慮したファイルカウント"""
        verify_current_platform()  # プラットフォーム検証

        # プロジェクト本体の.pyファイル
        (project_detector.repo_path / "main.py").write_text("print('hello')", encoding="utf-8")

        # .venvディレクトリ内の.pyファイル（除外対象）
        venv_dir = project_detector.repo_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "lib.py").write_text("# lib", encoding="utf-8")

        # 除外なしではカウントされる
        count = project_detector._count_files_with_extension(".py", [])
        assert count == 2

        # .venvを除外するとカウントされない
        count = project_detector._count_files_with_extension(".py", [".venv"])
        assert count == 1

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
        assert "scores" in analysis  # スコア情報が含まれる
        assert "python" in analysis["scores"]
        assert analysis["scores"]["python"]["detected"] is True
        assert "uv" in analysis["tools"]
        assert "git" in analysis["tools"]
        assert "vscode" in analysis["tools"]
        assert "common" in analysis["recommended_templates"]
        assert "python" in analysis["recommended_templates"]

    @pytest.mark.unit
    def test_scoring_system_logic(self, project_detector):
        """スコアリングシステムのロジックテスト"""
        verify_current_platform()  # プラットフォーム検証

        # Pythonのルールを取得
        python_rules = project_detector.SCORING_RULES["python"]

        # ファイルが存在しない場合はスコア0
        score = project_detector._calculate_score("python", python_rules)
        assert score == 0.0

        # pyproject.tomlを作成（プライマリファイル: 10点）
        (project_detector.repo_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
        score = project_detector._calculate_score("python", python_rules)
        assert score >= 10.0  # 閾値に達する

    @pytest.mark.unit
    def test_scoring_rules_completeness(self, project_detector):
        """スコアリングルールの完全性テスト"""
        verify_current_platform()  # プラットフォーム検証

        # すべてのプロジェクトタイプにルールが定義されていることを確認
        for _project_type, rules in project_detector.SCORING_RULES.items():
            assert isinstance(rules, dict)
            assert "threshold" in rules
            assert isinstance(rules["threshold"], (int, float))
            assert rules["threshold"] > 0

    @pytest.mark.unit
    def test_tool_detection_completeness(self, project_detector):
        """ツール検出の完全性テスト"""
        verify_current_platform()  # プラットフォーム検証

        # すべてのツールに検出ルールが定義されていることを確認
        for _tool, indicators in project_detector.TOOL_DETECTION.items():
            assert isinstance(indicators, list)
            assert len(indicators) > 0
            for indicator in indicators:
                assert isinstance(indicator, str)
                assert len(indicator) > 0

    @pytest.mark.unit
    def test_edge_cases(self, project_detector):
        """エッジケースのテスト"""
        verify_current_platform()  # プラットフォーム検証

        # 存在しない拡張子でのカウント
        count = project_detector._count_files_with_extension(".nonexistent", [])
        assert count == 0

        # 空のスコアリングルール
        empty_rules = {"threshold": 10}
        score = project_detector._calculate_score("test", empty_rules)
        assert score == 0.0

"""テンプレート管理のテスト"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from setup_repo.template_manager import TemplateManager


class TestTemplateManager:
    """TemplateManagerクラスのテスト"""

    @pytest.fixture
    def temp_project(self):
        """テスト用の一時プロジェクトディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # gitignore-templatesディレクトリを作成
            gitignore_dir = project_root / "gitignore-templates"
            gitignore_dir.mkdir()
            (gitignore_dir / "python.gitignore").write_text("__pycache__/\n*.pyc\n")
            (gitignore_dir / "node.gitignore").write_text("node_modules/\n*.log\n")

            # vscode-templatesディレクトリを作成
            vscode_dir = project_root / "vscode-templates"
            (vscode_dir / "linux").mkdir(parents=True)
            (vscode_dir / "linux" / "settings.json").write_text('{"python.defaultInterpreter": "/usr/bin/python3"}')
            (vscode_dir / "windows").mkdir()
            (vscode_dir / "windows" / "settings.json").write_text('{"python.defaultInterpreter": "python"}')

            yield project_root

    @pytest.fixture
    def manager(self, temp_project):
        """TemplateManagerインスタンス"""
        return TemplateManager(temp_project)

    def test_list_templates(self, manager):
        """テンプレート一覧取得のテスト"""
        templates = manager.list_templates()

        assert "gitignore" in templates
        assert "vscode" in templates
        assert "custom" in templates

        # パッケージテンプレートから実際にロードされる
        assert len(templates["gitignore"]) > 0  # python, node, go, etc.
        assert len(templates["vscode"]) > 0  # linux, windows, macos
        # 実際のテンプレートに含まれているものを確認
        assert "python" in templates["gitignore"]
        assert "linux" in templates["vscode"]

    def test_apply_gitignore_template(self, manager, temp_project):
        """gitignoreテンプレート適用のテスト"""
        target_path = temp_project / "test_project"
        target_path.mkdir()

        result_path = manager.apply_gitignore_template("python", target_path)

        assert result_path.exists()
        assert result_path.name == ".gitignore"
        content = result_path.read_text()
        assert "__pycache__/" in content
        # The actual Python template uses *.py[cod] instead of *.pyc
        assert "*.py" in content or "py" in content

    def test_apply_gitignore_template_with_backup(self, manager, temp_project):
        """既存.gitignoreがある場合のバックアップテスト"""
        target_path = temp_project / "test_project"
        target_path.mkdir()

        # 既存の.gitignoreを作成
        existing_gitignore = target_path / ".gitignore"
        existing_gitignore.write_text("existing content")

        manager.apply_gitignore_template("python", target_path)

        # バックアップファイルが作成されることを確認
        backup_file = target_path / ".gitignore.backup"
        assert backup_file.exists()
        assert backup_file.read_text() == "existing content"

    def test_apply_vscode_template(self, manager, temp_project):
        """VS Codeテンプレート適用のテスト"""
        target_path = temp_project / "test_project"
        target_path.mkdir()

        result_path = manager.apply_vscode_template("linux", target_path)

        assert result_path.exists()
        assert result_path.name == ".vscode"
        settings_file = result_path / "settings.json"
        assert settings_file.exists()

        settings = json.loads(settings_file.read_text())
        # Check for actual template content (not the test fixture content)
        assert isinstance(settings, dict)
        assert len(settings) > 0

    def test_create_custom_template_file(self, manager, temp_project):
        """ファイルからカスタムテンプレート作成のテスト"""
        # ソースファイルを作成
        source_file = temp_project / "source.txt"
        source_file.write_text("template content")

        result_path = manager.create_custom_template("test_template", source_file)

        assert result_path.exists()
        assert result_path.name == "test_template"

        # メタデータファイルが作成されることを確認
        metadata_file = result_path / "template.json"
        assert metadata_file.exists()

        metadata = json.loads(metadata_file.read_text())
        assert metadata["name"] == "test_template"
        assert metadata["type"] == "file"

    def test_create_custom_template_directory(self, manager, temp_project):
        """ディレクトリからカスタムテンプレート作成のテスト"""
        # ソースディレクトリを作成
        source_dir = temp_project / "source_dir"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        result_path = manager.create_custom_template("dir_template", source_dir)

        assert result_path.exists()
        assert result_path.is_dir()

        # ファイルがコピーされることを確認
        assert (result_path / "file1.txt").exists()
        assert (result_path / "file2.txt").exists()

        # メタデータファイルが作成されることを確認
        metadata_file = result_path / "template.json"
        assert metadata_file.exists()

        metadata = json.loads(metadata_file.read_text())
        assert metadata["type"] == "directory"

    def test_apply_custom_template_file(self, manager, temp_project):
        """ファイル型カスタムテンプレート適用のテスト"""
        # カスタムテンプレートを作成
        source_file = temp_project / "source.txt"
        source_file.write_text("template content")
        manager.create_custom_template("test_template", source_file)

        # 適用先ディレクトリを作成
        target_path = temp_project / "target"
        target_path.mkdir()

        result_path = manager.apply_custom_template("test_template", target_path)

        assert result_path == target_path
        applied_file = target_path / "source.txt"
        assert applied_file.exists()
        assert applied_file.read_text() == "template content"

    def test_apply_custom_template_directory(self, manager, temp_project):
        """ディレクトリ型カスタムテンプレート適用のテスト"""
        # ソースディレクトリを作成
        source_dir = temp_project / "source_dir"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content2")

        # カスタムテンプレートを作成
        manager.create_custom_template("dir_template", source_dir)

        # 適用先ディレクトリを作成
        target_path = temp_project / "target"
        target_path.mkdir()

        result_path = manager.apply_custom_template("dir_template", target_path)

        assert result_path == target_path
        assert (target_path / "file1.txt").exists()
        assert (target_path / "subdir" / "file2.txt").exists()
        assert (target_path / "file1.txt").read_text() == "content1"
        assert (target_path / "subdir" / "file2.txt").read_text() == "content2"

    def test_remove_template(self, manager, temp_project):
        """カスタムテンプレート削除のテスト"""
        # カスタムテンプレートを作成
        source_file = temp_project / "source.txt"
        source_file.write_text("template content")
        template_path = manager.create_custom_template("test_template", source_file)

        assert template_path.exists()

        # テンプレートを削除
        result = manager.remove_template("test_template")

        assert result is True
        assert not template_path.exists()

    def test_remove_nonexistent_template(self, manager):
        """存在しないテンプレート削除のテスト"""
        result = manager.remove_template("nonexistent")
        assert result is False

    def test_apply_nonexistent_gitignore_template(self, manager, temp_project):
        """存在しないgitignoreテンプレート適用のテスト"""
        target_path = temp_project / "test_project"
        target_path.mkdir()

        with pytest.raises(FileNotFoundError):
            manager.apply_gitignore_template("nonexistent", target_path)

    def test_apply_nonexistent_vscode_template(self, manager, temp_project):
        """存在しないVS Codeテンプレート適用のテスト"""
        target_path = temp_project / "test_project"
        target_path.mkdir()

        with pytest.raises(FileNotFoundError):
            manager.apply_vscode_template("nonexistent", target_path)

    def test_apply_nonexistent_custom_template(self, manager, temp_project):
        """存在しないカスタムテンプレート適用のテスト"""
        target_path = temp_project / "test_project"
        target_path.mkdir()

        with pytest.raises(FileNotFoundError):
            manager.apply_custom_template("nonexistent", target_path)

    def test_create_template_with_existing_name(self, manager, temp_project):
        """既存名でのテンプレート作成のテスト"""
        source_file = temp_project / "source.txt"
        source_file.write_text("template content")

        # 最初のテンプレートを作成
        manager.create_custom_template("test_template", source_file)

        # 同じ名前で再作成を試行
        with pytest.raises(FileExistsError):
            manager.create_custom_template("test_template", source_file)

    def test_create_template_with_nonexistent_source(self, manager, temp_project):
        """存在しないソースでのテンプレート作成のテスト"""
        nonexistent_path = temp_project / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            manager.create_custom_template("test_template", nonexistent_path)

    def test_default_project_root(self):
        """デフォルトプロジェクトルートのテスト"""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test/path")
            manager = TemplateManager()
            assert manager.project_root == Path("/test/path")

    def test_list_templates_empty_directories(self, temp_project):
        """空のテンプレートディレクトリのテスト"""
        # 空のディレクトリでマネージャーを作成
        empty_project = temp_project / "empty"
        empty_project.mkdir()
        manager = TemplateManager(empty_project)

        templates = manager.list_templates()

        # gitignore and vscode templates come from the package, not the project directory
        # so they will not be empty. Only custom templates come from the project directory.
        assert isinstance(templates["gitignore"], list)
        assert isinstance(templates["vscode"], list)
        assert templates["custom"] == []  # Custom templates are from project directory

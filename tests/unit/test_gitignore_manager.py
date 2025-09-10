"""GitignoreManagerのテスト"""

import pytest
from pathlib import Path
from setup_repo.gitignore_manager import GitignoreManager


@pytest.mark.unit
class TestGitignoreManager:
    """GitignoreManagerクラスのテスト"""

    def test_init_with_default_templates_dir(self, temp_dir):
        """デフォルトテンプレートディレクトリでの初期化テスト"""
        manager = GitignoreManager(temp_dir)
        assert manager.repo_path == temp_dir
        assert manager.gitignore_path == temp_dir / ".gitignore"

    def test_init_with_custom_templates_dir(self, temp_dir):
        """カスタムテンプレートディレクトリでの初期化テスト"""
        custom_templates = temp_dir / "custom-templates"
        manager = GitignoreManager(temp_dir, custom_templates)
        assert manager.templates_dir == custom_templates

    def test_get_available_templates(self, temp_dir):
        """利用可能テンプレート一覧取得テスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()
        
        # テストテンプレートファイルを作成
        (templates_dir / "python.gitignore").write_text("# Python\n__pycache__/")
        (templates_dir / "node.gitignore").write_text("# Node\nnode_modules/")
        
        manager = GitignoreManager(temp_dir, templates_dir)
        templates = manager.get_available_templates()
        
        assert "python" in templates
        assert "node" in templates
        assert len(templates) == 2

    def test_load_template(self, temp_dir):
        """テンプレート読み込みテスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()
        
        template_content = "# Python\n__pycache__/\n*.pyc"
        (templates_dir / "python.gitignore").write_text(template_content)
        
        manager = GitignoreManager(temp_dir, templates_dir)
        loaded_content = manager.load_template("python")
        
        assert loaded_content == template_content

    def test_load_nonexistent_template(self, temp_dir):
        """存在しないテンプレート読み込みテスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()
        
        manager = GitignoreManager(temp_dir, templates_dir)
        loaded_content = manager.load_template("nonexistent")
        
        assert loaded_content == ""

    def test_setup_gitignore_from_templates(self, temp_dir):
        """テンプレートから.gitignore作成テスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()
        
        # テストテンプレートを作成
        (templates_dir / "common.gitignore").write_text("# Common\n.DS_Store")
        (templates_dir / "python.gitignore").write_text("# Python\n__pycache__/")
        
        manager = GitignoreManager(temp_dir, templates_dir)
        result = manager.setup_gitignore_from_templates(["common", "python"])
        
        assert result is True
        assert manager.gitignore_path.exists()
        
        content = manager.gitignore_path.read_text()
        assert "# Common" in content
        assert ".DS_Store" in content
        assert "# Python" in content
        assert "__pycache__/" in content

    def test_protection_mode_functionality(self, temp_dir):
        """保護モード機能テスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()
        
        # テストテンプレートを作成
        (templates_dir / "python.gitignore").write_text("__pycache__/\n*.pyc")
        
        # 既存.gitignoreを作成
        existing_content = "# Existing\n*.log\n"
        gitignore_path = temp_dir / ".gitignore"
        gitignore_path.write_text(existing_content)
        
        manager = GitignoreManager(temp_dir, templates_dir)
        result = manager.setup_gitignore_from_templates(["python"], merge_mode=False)
        
        assert result is True
        
        final_content = gitignore_path.read_text()
        # 既存コンテンツのみで、新しいエントリは追加されない
        assert final_content == existing_content

    def test_setup_gitignore_dry_run(self, temp_dir, capsys):
        """ドライランモードテスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()
        
        manager = GitignoreManager(temp_dir, templates_dir)
        result = manager.setup_gitignore_from_templates(["python"], dry_run=True)
        
        assert result is True
        assert not manager.gitignore_path.exists()
        
        captured = capsys.readouterr()
        assert "テンプレート使用予定" in captured.out

    def test_get_current_entries(self, temp_dir):
        """現在のエントリ取得テスト"""
        gitignore_content = """# Test
*.log
__pycache__/
# Comment
.venv/
"""
        gitignore_path = temp_dir / ".gitignore"
        gitignore_path.write_text(gitignore_content)
        
        manager = GitignoreManager(temp_dir)
        entries = manager.get_current_entries()
        
        assert "*.log" in entries
        assert "__pycache__/" in entries
        assert ".venv/" in entries
        assert "# Comment" not in entries  # コメントは除外

    def test_add_entries(self, temp_dir):
        """エントリ追加テスト"""
        manager = GitignoreManager(temp_dir)
        
        # 初期.gitignoreを作成
        manager.gitignore_path.write_text("# Initial\n*.log\n")
        
        new_entries = ["*.tmp", "build/"]
        result = manager.add_entries(new_entries)
        
        assert result is True
        
        content = manager.gitignore_path.read_text()
        assert "*.tmp" in content
        assert "build/" in content
        assert "*.log" in content  # 既存エントリも保持

    def test_add_duplicate_entries(self, temp_dir):
        """重複エントリ追加テスト"""
        manager = GitignoreManager(temp_dir)
        
        # 初期.gitignoreを作成
        manager.gitignore_path.write_text("# Initial\n*.log\n")
        
        # 既存エントリを含む新しいエントリ
        new_entries = ["*.log", "*.tmp"]
        result = manager.add_entries(new_entries)
        
        assert result is True
        
        content = manager.gitignore_path.read_text()
        # *.logは重複しないはず
        assert content.count("*.log") == 1
        assert "*.tmp" in content

    def test_merge_mode_functionality(self, temp_dir):
        """マージモード機能テスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()
        
        # テストテンプレートを作成
        (templates_dir / "python.gitignore").write_text("__pycache__/\n*.pyc")
        
        # 既存.gitignoreを作成
        existing_content = "# Existing\n*.log\n"
        gitignore_path = temp_dir / ".gitignore"
        gitignore_path.write_text(existing_content)
        
        manager = GitignoreManager(temp_dir, templates_dir)
        result = manager.setup_gitignore_from_templates(["python"], merge_mode=True)
        
        assert result is True
        
        final_content = gitignore_path.read_text()
        assert "# Existing" in final_content
        assert "*.log" in final_content
        assert "__pycache__/" in final_content
        assert "*.pyc" in final_content
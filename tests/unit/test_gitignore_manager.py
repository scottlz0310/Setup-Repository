"""GitignoreManagerのテスト"""

from unittest.mock import patch

import pytest

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

    def test_ensure_gitignore_exists_when_missing(self, temp_dir):
        """gitignoreが存在しない場合の作成テスト"""
        manager = GitignoreManager(temp_dir)

        # .gitignoreが存在しないことを確認
        assert not manager.gitignore_path.exists()

        # setup_gitignoreをモック
        with patch.object(manager, "setup_gitignore", return_value=True) as mock_setup:
            result = manager.ensure_gitignore_exists()

            assert result is True
            mock_setup.assert_called_once_with(False)

    def test_ensure_gitignore_exists_when_present(self, temp_dir):
        """gitignoreが既に存在する場合のテスト"""
        manager = GitignoreManager(temp_dir)

        # .gitignoreを作成
        manager.gitignore_path.write_text("# Existing")

        result = manager.ensure_gitignore_exists()
        assert result is True

    def test_ensure_gitignore_exists_dry_run(self, temp_dir):
        """ドライランモードでのgitignore作成テスト"""
        manager = GitignoreManager(temp_dir)

        with patch.object(manager, "setup_gitignore", return_value=True) as mock_setup:
            result = manager.ensure_gitignore_exists(dry_run=True)

            assert result is True
            mock_setup.assert_called_once_with(True)

    def test_get_current_entries_empty_file(self, temp_dir):
        """空の.gitignoreファイルのテスト"""
        manager = GitignoreManager(temp_dir)
        manager.gitignore_path.write_text("")

        entries = manager.get_current_entries()
        assert entries == set()

    def test_get_current_entries_only_comments(self, temp_dir):
        """コメントのみの.gitignoreファイルのテスト"""
        manager = GitignoreManager(temp_dir)
        manager.gitignore_path.write_text("# Comment 1\n# Comment 2\n")

        entries = manager.get_current_entries()
        assert entries == set()

    def test_get_current_entries_with_whitespace(self, temp_dir):
        """空白を含む.gitignoreファイルのテスト"""
        gitignore_content = """
# Comment
*.log

__pycache__/

# Another comment
.venv/
"""
        manager = GitignoreManager(temp_dir)
        manager.gitignore_path.write_text(gitignore_content)

        entries = manager.get_current_entries()
        expected = {"*.log", "__pycache__/", ".venv/"}
        assert entries == expected

    def test_get_current_entries_file_read_error(self, temp_dir):
        """ファイル読み込みエラーのテスト"""
        manager = GitignoreManager(temp_dir)

        # 存在しないファイルを指定
        manager.gitignore_path = temp_dir / "nonexistent.gitignore"

        entries = manager.get_current_entries()
        assert entries == set()

    def test_add_entries_empty_list(self, temp_dir):
        """空のエントリリストの追加テスト"""
        manager = GitignoreManager(temp_dir)

        result = manager.add_entries([])
        assert result is True

    def test_add_entries_to_nonexistent_file(self, temp_dir):
        """存在しないファイルへのエントリ追加テスト"""
        manager = GitignoreManager(temp_dir)

        new_entries = ["*.tmp", "build/"]
        result = manager.add_entries(new_entries)

        assert result is True
        assert manager.gitignore_path.exists()

        content = manager.gitignore_path.read_text()
        assert "*.tmp" in content
        assert "build/" in content

    def test_add_entries_dry_run_mode(self, temp_dir, capsys):
        """ドライランモードでのエントリ追加テスト"""
        manager = GitignoreManager(temp_dir)

        new_entries = ["*.tmp", "build/"]
        result = manager.add_entries(new_entries, dry_run=True)

        assert result is True
        assert not manager.gitignore_path.exists()

        captured = capsys.readouterr()
        assert "追加予定エントリ" in captured.out

    def test_add_entries_file_without_newline(self, temp_dir):
        """改行で終わらないファイルへのエントリ追加テスト"""
        manager = GitignoreManager(temp_dir)

        # 改行で終わらない初期コンテンツ
        manager.gitignore_path.write_text("*.log")

        new_entries = ["*.tmp"]
        result = manager.add_entries(new_entries)

        assert result is True

        content = manager.gitignore_path.read_text()
        assert "*.log\n" in content
        assert "*.tmp" in content

    def test_add_entries_write_error(self, temp_dir):
        """ファイル書き込みエラーのテスト"""
        manager = GitignoreManager(temp_dir)

        # 書き込み不可能なファイルを作成
        manager.gitignore_path.write_text("existing content")
        manager.gitignore_path.chmod(0o444)  # 読み取り専用

        new_entries = ["*.tmp"]
        result = manager.add_entries(new_entries)

        assert result is False

        # 権限を戻す（クリーンアップのため）
        manager.gitignore_path.chmod(0o644)

    def test_load_template_read_error(self, temp_dir):
        """テンプレート読み込みエラーのテスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()

        # 存在しないテンプレートでエラーを発生させる
        manager = GitignoreManager(temp_dir, templates_dir)

        # ファイル読み込みエラーをシミュレート
        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            content = manager.load_template("python")

        assert content == ""

    def test_get_available_templates_no_directory(self, temp_dir):
        """テンプレートディレクトリが存在しない場合のテスト"""
        nonexistent_dir = temp_dir / "nonexistent"
        manager = GitignoreManager(temp_dir, nonexistent_dir)

        templates = manager.get_available_templates()
        assert templates == []

    def test_setup_gitignore_from_templates_no_valid_templates(self, temp_dir):
        """有効なテンプレートがない場合のテスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()

        manager = GitignoreManager(temp_dir, templates_dir)
        result = manager.setup_gitignore_from_templates(["nonexistent"])

        assert result is False

    def test_create_new_gitignore_write_error(self, temp_dir):
        """新規.gitignore作成時の書き込みエラーテスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()

        # テストテンプレートを作成
        (templates_dir / "python.gitignore").write_text("__pycache__/")

        manager = GitignoreManager(temp_dir, templates_dir)

        # ファイル書き込みエラーをシミュレート
        with patch("pathlib.Path.write_text", side_effect=OSError("Permission denied")):
            result = manager._create_new_gitignore(["python"])

        assert result is False

    def test_merge_with_existing_read_error(self, temp_dir):
        """既存ファイルとのマージ時の読み込みエラーテスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()

        # テストテンプレートを作成
        (templates_dir / "python.gitignore").write_text("__pycache__/")

        # 読み取り不可能な.gitignoreを作成
        manager = GitignoreManager(temp_dir, templates_dir)
        manager.gitignore_path.write_text("existing")
        manager.gitignore_path.chmod(0o000)

        result = manager._merge_with_existing(["python"])

        assert result is False

        # 権限を戻す（クリーンアップのため）
        manager.gitignore_path.chmod(0o644)

    def test_merge_with_existing_no_new_entries(self, temp_dir):
        """マージ時に新しいエントリがない場合のテスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()

        # 既存エントリと同じテンプレートを作成
        (templates_dir / "python.gitignore").write_text("*.log")

        # 既存.gitignoreを作成
        manager = GitignoreManager(temp_dir, templates_dir)
        manager.gitignore_path.write_text("*.log\n")

        result = manager._merge_with_existing(["python"])

        assert result is True

    def test_setup_gitignore_with_project_detector(self, temp_dir):
        """プロジェクト検出器を使用した.gitignoreセットアップのテスト"""
        # Python プロジェクトファイルを作成
        (temp_dir / "pyproject.toml").write_text("[tool.poetry]")

        # テンプレートディレクトリを作成
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "python.gitignore").write_text("__pycache__/\n*.pyc")
        (templates_dir / "common.gitignore").write_text(".DS_Store")

        manager = GitignoreManager(temp_dir, templates_dir)
        result = manager.setup_gitignore()

        assert result is True
        assert manager.gitignore_path.exists()

        content = manager.gitignore_path.read_text()
        assert "__pycache__/" in content or ".DS_Store" in content

    def test_merge_with_existing_write_error(self, temp_dir):
        """マージ時の書き込みエラーテスト"""
        templates_dir = temp_dir / "templates"
        templates_dir.mkdir()

        # テストテンプレートを作成
        (templates_dir / "python.gitignore").write_text("__pycache__/")

        # 既存.gitignoreを作成
        manager = GitignoreManager(temp_dir, templates_dir)
        manager.gitignore_path.write_text("existing")

        # ファイルを読み取り専用にして書き込みエラーを発生させる
        manager.gitignore_path.chmod(0o444)

        result = manager._merge_with_existing(["python"])

        assert result is False

        # 権限を戻す（クリーンアップのため）
        manager.gitignore_path.chmod(0o644)

    def test_get_current_entries_oserror_handling(self, temp_dir):
        """OSErrorハンドリングのテスト"""
        manager = GitignoreManager(temp_dir)

        # 存在しないファイルでOSErrorを発生させる
        manager.gitignore_path = temp_dir / "nonexistent" / ".gitignore"

        entries = manager.get_current_entries()
        assert entries == set()

    def test_add_entries_oserror_handling(self, temp_dir):
        """add_entriesでのOSErrorハンドリングテスト"""
        manager = GitignoreManager(temp_dir)

        # 初期ファイルを作成
        manager.gitignore_path.write_text("existing")

        # ファイルを読み取り専用にして書き込みエラーを発生させる
        manager.gitignore_path.chmod(0o444)

        new_entries = ["*.tmp"]
        result = manager.add_entries(new_entries)

        assert result is False

        # 権限を戻す（クリーンアップのため）
        manager.gitignore_path.chmod(0o644)

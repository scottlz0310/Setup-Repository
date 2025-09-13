"""GitignoreManagerのテスト"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from ..multiplatform.helpers import verify_current_platform, skip_if_not_platform

from src.setup_repo.gitignore_manager import GitignoreManager


@pytest.fixture
def temp_repo_path(tmp_path):
    """テスト用リポジトリパス"""
    return tmp_path / "test_repo"


@pytest.fixture
def temp_templates_dir(tmp_path):
    """テスト用テンプレートディレクトリ"""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    
    # サンプルテンプレートファイルを作成
    (templates_dir / "python.gitignore").write_text(
        "# Python\n__pycache__/\n*.pyc\n.venv/\n", encoding="utf-8"
    )
    (templates_dir / "node.gitignore").write_text(
        "# Node.js\nnode_modules/\n*.log\n", encoding="utf-8"
    )
    
    return templates_dir


@pytest.fixture
def gitignore_manager(temp_repo_path, temp_templates_dir):
    """GitignoreManagerインスタンス"""
    temp_repo_path.mkdir(parents=True)
    return GitignoreManager(temp_repo_path, temp_templates_dir)


class TestGitignoreManager:
    """GitignoreManagerのテストクラス"""

    @pytest.mark.unit
    def test_init_with_custom_templates_dir(self, temp_repo_path, temp_templates_dir):
        """カスタムテンプレートディレクトリでの初期化"""
        platform_info = verify_current_platform()
        
        manager = GitignoreManager(temp_repo_path, temp_templates_dir)
        
        assert manager.repo_path == Path(temp_repo_path)
        assert manager.templates_dir == Path(temp_templates_dir)
        assert manager.gitignore_path == Path(temp_repo_path) / ".gitignore"

    @pytest.mark.unit
    def test_init_with_default_templates_dir(self, temp_repo_path):
        """デフォルトテンプレートディレクトリでの初期化"""
        platform_info = verify_current_platform()
        
        manager = GitignoreManager(temp_repo_path)
        
        assert manager.repo_path == Path(temp_repo_path)
        # デフォルトパスの確認
        expected_default = Path(__file__).parent.parent.parent.parent / "gitignore-templates"
        assert manager.templates_dir == expected_default

    @pytest.mark.unit
    def test_ensure_gitignore_exists_when_exists(self, gitignore_manager):
        """既存.gitignoreファイルがある場合"""
        platform_info = verify_current_platform()
        
        # .gitignoreファイルを作成
        gitignore_manager.gitignore_path.write_text("# Existing", encoding="utf-8")
        
        result = gitignore_manager.ensure_gitignore_exists()
        
        assert result is True

    @pytest.mark.unit
    def test_get_current_entries_empty_file(self, gitignore_manager):
        """空の.gitignoreファイルの場合"""
        platform_info = verify_current_platform()
        
        gitignore_manager.gitignore_path.write_text("", encoding="utf-8")
        
        entries = gitignore_manager.get_current_entries()
        
        assert entries == set()

    @pytest.mark.unit
    def test_get_current_entries_with_content(self, gitignore_manager):
        """.gitignoreファイルにコンテンツがある場合"""
        platform_info = verify_current_platform()
        
        content = """# Comment
__pycache__/
*.pyc

# Another comment
.venv/
"""
        gitignore_manager.gitignore_path.write_text(content, encoding="utf-8")
        
        entries = gitignore_manager.get_current_entries()
        
        expected = {"__pycache__/", "*.pyc", ".venv/"}
        assert entries == expected

    @pytest.mark.unit
    def test_get_current_entries_nonexistent_file(self, gitignore_manager):
        """存在しない.gitignoreファイルの場合"""
        platform_info = verify_current_platform()
        
        entries = gitignore_manager.get_current_entries()
        
        assert entries == set()

    @pytest.mark.unit
    def test_add_entries_new_entries(self, gitignore_manager):
        """新しいエントリの追加"""
        platform_info = verify_current_platform()
        
        # 既存の.gitignoreを作成
        gitignore_manager.gitignore_path.write_text("__pycache__/\n", encoding="utf-8")
        
        new_entries = ["*.pyc", ".venv/"]
        result = gitignore_manager.add_entries(new_entries)
        
        assert result is True
        
        # ファイル内容を確認
        content = gitignore_manager.gitignore_path.read_text(encoding="utf-8")
        assert "*.pyc" in content
        assert ".venv/" in content
        assert "__pycache__/" in content

    @pytest.mark.unit
    def test_add_entries_duplicate_entries(self, gitignore_manager):
        """重複エントリの追加（スキップされる）"""
        platform_info = verify_current_platform()
        
        # 既存の.gitignoreを作成
        gitignore_manager.gitignore_path.write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
        
        new_entries = ["*.pyc", ".venv/"]  # *.pycは重複
        result = gitignore_manager.add_entries(new_entries)
        
        assert result is True
        
        # ファイル内容を確認（重複は追加されない）
        content = gitignore_manager.gitignore_path.read_text(encoding="utf-8")
        assert content.count("*.pyc") == 1
        assert ".venv/" in content

    @pytest.mark.unit
    def test_add_entries_dry_run(self, gitignore_manager, capsys):
        """ドライランモードでのエントリ追加"""
        platform_info = verify_current_platform()
        
        new_entries = ["*.pyc", ".venv/"]
        result = gitignore_manager.add_entries(new_entries, dry_run=True)
        
        assert result is True
        assert not gitignore_manager.gitignore_path.exists()
        
        # 出力メッセージを確認
        captured = capsys.readouterr()
        assert "追加予定エントリ" in captured.out

    @pytest.mark.unit
    def test_load_template_existing(self, gitignore_manager):
        """既存テンプレートの読み込み"""
        platform_info = verify_current_platform()
        
        content = gitignore_manager.load_template("python")
        
        assert "# Python" in content
        assert "__pycache__/" in content

    @pytest.mark.unit
    def test_load_template_nonexistent(self, gitignore_manager):
        """存在しないテンプレートの読み込み"""
        platform_info = verify_current_platform()
        
        content = gitignore_manager.load_template("nonexistent")
        
        assert content == ""

    @pytest.mark.unit
    def test_get_available_templates(self, gitignore_manager):
        """利用可能なテンプレート一覧の取得"""
        platform_info = verify_current_platform()
        
        templates = gitignore_manager.get_available_templates()
        
        assert "python" in templates
        assert "node" in templates
        assert templates == sorted(templates)  # ソートされている

    @pytest.mark.unit
    def test_get_available_templates_no_dir(self, temp_repo_path):
        """テンプレートディレクトリが存在しない場合"""
        platform_info = verify_current_platform()
        
        nonexistent_dir = temp_repo_path / "nonexistent"
        manager = GitignoreManager(temp_repo_path, nonexistent_dir)
        
        templates = manager.get_available_templates()
        
        assert templates == []

    @pytest.mark.unit
    def test_create_new_gitignore(self, gitignore_manager):
        """新規.gitignore作成"""
        platform_info = verify_current_platform()
        
        result = gitignore_manager._create_new_gitignore(["python", "node"])
        
        assert result is True
        assert gitignore_manager.gitignore_path.exists()
        
        content = gitignore_manager.gitignore_path.read_text(encoding="utf-8")
        assert "# Python" in content
        assert "# Node" in content
        assert "__pycache__/" in content
        assert "node_modules/" in content

    @pytest.mark.unit
    def test_create_new_gitignore_no_templates(self, gitignore_manager):
        """利用可能なテンプレートがない場合"""
        platform_info = verify_current_platform()
        
        result = gitignore_manager._create_new_gitignore(["nonexistent"])
        
        assert result is False
        assert not gitignore_manager.gitignore_path.exists()

    @pytest.mark.unit
    def test_merge_with_existing(self, gitignore_manager):
        """既存.gitignoreとのマージ"""
        platform_info = verify_current_platform()
        
        # 既存の.gitignoreを作成
        existing_content = "# Existing\n.DS_Store\n"
        gitignore_manager.gitignore_path.write_text(existing_content, encoding="utf-8")
        
        result = gitignore_manager._merge_with_existing(["python"])
        
        assert result is True
        
        content = gitignore_manager.gitignore_path.read_text(encoding="utf-8")
        assert ".DS_Store" in content  # 既存エントリ
        assert "__pycache__/" in content  # 新しいエントリ

    @pytest.mark.unit
    def test_merge_with_existing_no_new_entries(self, gitignore_manager):
        """マージで新しいエントリがない場合"""
        platform_info = verify_current_platform()
        
        # 既存の.gitignoreにPythonテンプレートの内容を含める
        existing_content = "# Existing\n__pycache__/\n*.pyc\n.venv/\n"
        gitignore_manager.gitignore_path.write_text(existing_content, encoding="utf-8")
        
        result = gitignore_manager._merge_with_existing(["python"])
        
        assert result is True

    @pytest.mark.unit
    def test_setup_gitignore_from_templates_new_file(self, gitignore_manager):
        """テンプレートから新規.gitignore作成"""
        platform_info = verify_current_platform()
        
        result = gitignore_manager.setup_gitignore_from_templates(["python"])
        
        assert result is True
        assert gitignore_manager.gitignore_path.exists()

    @pytest.mark.unit
    def test_setup_gitignore_from_templates_merge_mode(self, gitignore_manager):
        """マージモードでのテンプレート適用"""
        platform_info = verify_current_platform()
        
        # 既存ファイルを作成
        gitignore_manager.gitignore_path.write_text("# Existing\n", encoding="utf-8")
        
        result = gitignore_manager.setup_gitignore_from_templates(["python"], merge_mode=True)
        
        assert result is True

    @pytest.mark.unit
    def test_setup_gitignore_from_templates_no_merge(self, gitignore_manager):
        """非マージモードでの既存ファイル処理"""
        platform_info = verify_current_platform()
        
        # 既存ファイルを作成
        gitignore_manager.gitignore_path.write_text("# Existing\n", encoding="utf-8")
        
        result = gitignore_manager.setup_gitignore_from_templates(["python"], merge_mode=False)
        
        assert result is True

    @pytest.mark.unit
    def test_setup_gitignore_dry_run(self, gitignore_manager, capsys):
        """ドライランモードでのセットアップ"""
        platform_info = verify_current_platform()
        
        result = gitignore_manager.setup_gitignore_from_templates(["python"], dry_run=True)
        
        assert result is True
        assert not gitignore_manager.gitignore_path.exists()
        
        captured = capsys.readouterr()
        assert "テンプレート使用予定" in captured.out

    @pytest.mark.unit
    @patch('src.setup_repo.gitignore_manager.ProjectDetector')
    def test_setup_gitignore_auto_detect(self, mock_detector_class, gitignore_manager, capsys):
        """プロジェクトタイプ自動検出でのセットアップ"""
        platform_info = verify_current_platform()
        
        # ProjectDetectorのモック設定
        mock_detector = Mock()
        mock_detector.get_recommended_templates.return_value = ["python"]
        mock_detector.analyze_project.return_value = {
            'project_types': ['python'],
            'tools': ['pytest']
        }
        mock_detector_class.return_value = mock_detector
        
        result = gitignore_manager.setup_gitignore()
        
        assert result is True
        mock_detector_class.assert_called_once_with(gitignore_manager.repo_path)
        
        captured = capsys.readouterr()
        assert "検出されたプロジェクトタイプ" in captured.out

    @pytest.mark.unit
    def test_file_operation_error_handling(self, gitignore_manager):
        """ファイル操作エラーのハンドリング"""
        platform_info = verify_current_platform()
        
        # 読み取り専用ディレクトリを作成してエラーを発生させる
        with patch('pathlib.Path.write_text', side_effect=OSError("Permission denied")):
            result = gitignore_manager.add_entries(["*.pyc"])
            assert result is False

    @pytest.mark.unit
    def test_encoding_handling(self, gitignore_manager):
        """エンコーディングの適切な処理"""
        platform_info = verify_current_platform()
        
        # 日本語コメントを含むコンテンツ
        content = "# 日本語コメント\n__pycache__/\n"
        gitignore_manager.gitignore_path.write_text(content, encoding="utf-8")
        
        entries = gitignore_manager.get_current_entries()
        
        assert "__pycache__/" in entries
        
        # 新しいエントリを追加
        result = gitignore_manager.add_entries(["*.pyc"])
        assert result is True
        
        # 内容を確認
        updated_content = gitignore_manager.gitignore_path.read_text(encoding="utf-8")
        assert "日本語コメント" in updated_content
        assert "*.pyc" in updated_content
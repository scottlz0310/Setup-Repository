"""セキュリティチェック機能のテスト"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from src.setup_repo.safety_check import check_unpushed_changes, create_emergency_backup, prompt_user_action

from ..multiplatform.helpers import verify_current_platform


class TestCheckUnpushedChanges:
    """check_unpushed_changes関数のテスト"""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """テスト用リポジトリディレクトリ"""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        return repo

    @pytest.mark.unit
    def test_check_unpushed_changes_no_git(self, temp_repo):
        """Gitリポジトリでない場合"""
        verify_current_platform()  # プラットフォーム検証

        has_issues, issues = check_unpushed_changes(temp_repo)

        assert has_issues is False
        assert issues == []

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_unpushed_changes_clean_repo(self, mock_run, temp_repo):
        """クリーンなリポジトリの場合"""
        verify_current_platform()  # プラットフォーム検証

        # .gitディレクトリを作成
        (temp_repo / ".git").mkdir()

        # 全てのGitコマンドが空の結果を返すようにモック
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        has_issues, issues = check_unpushed_changes(temp_repo)

        assert has_issues is False
        assert issues == []

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_unpushed_changes_uncommitted_changes(self, mock_run, temp_repo):
        """未コミットの変更がある場合"""
        verify_current_platform()  # プラットフォーム検証

        # .gitディレクトリを作成
        (temp_repo / ".git").mkdir()

        def mock_git_command(cmd, **kwargs):
            if "status" in cmd:
                return Mock(returncode=0, stdout="M  modified_file.py\n", stderr="")
            else:
                return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_git_command

        has_issues, issues = check_unpushed_changes(temp_repo)

        assert has_issues is True
        assert "未コミットの変更があります" in issues

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_unpushed_changes_unpushed_commits(self, mock_run, temp_repo):
        """未pushのコミットがある場合"""
        verify_current_platform()  # プラットフォーム検証

        # .gitディレクトリを作成
        (temp_repo / ".git").mkdir()

        def mock_git_command(cmd, **kwargs):
            if "log" in cmd and "@{u}..HEAD" in cmd:
                return Mock(returncode=0, stdout="abc123 Latest commit\n", stderr="")
            else:
                return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_git_command

        has_issues, issues = check_unpushed_changes(temp_repo)

        assert has_issues is True
        assert "未pushのコミットがあります" in issues

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_unpushed_changes_stash_exists(self, mock_run, temp_repo):
        """stashがある場合"""
        verify_current_platform()  # プラットフォーム検証

        # .gitディレクトリを作成
        (temp_repo / ".git").mkdir()

        def mock_git_command(cmd, **kwargs):
            if "stash" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout="stash@{0}: WIP on main\n", stderr="")
            else:
                return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_git_command

        has_issues, issues = check_unpushed_changes(temp_repo)

        assert has_issues is True
        assert "stashがあります" in issues

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_unpushed_changes_multiple_issues(self, mock_run, temp_repo):
        """複数の問題がある場合"""
        verify_current_platform()  # プラットフォーム検証

        # .gitディレクトリを作成
        (temp_repo / ".git").mkdir()

        def mock_git_command(cmd, **kwargs):
            if "status" in cmd:
                return Mock(returncode=0, stdout="M  modified_file.py\n", stderr="")
            elif "stash" in cmd:
                return Mock(returncode=0, stdout="stash@{0}: WIP\n", stderr="")
            else:
                return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = mock_git_command

        has_issues, issues = check_unpushed_changes(temp_repo)

        assert has_issues is True
        assert len(issues) == 2
        assert "未コミットの変更があります" in issues
        assert "stashがあります" in issues

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_check_unpushed_changes_git_error(self, mock_run, temp_repo):
        """Gitコマンドエラーの場合"""
        verify_current_platform()  # プラットフォーム検証

        # .gitディレクトリを作成
        (temp_repo / ".git").mkdir()

        # Gitコマンドがエラーを返すようにモック
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        has_issues, issues = check_unpushed_changes(temp_repo)

        # エラーが発生してもクラッシュしないことを確認
        assert has_issues is False
        assert issues == []


class TestPromptUserAction:
    """prompt_user_action関数のテスト"""

    @pytest.mark.unit
    @patch("builtins.input")
    def test_prompt_user_action_skip(self, mock_input, capsys):
        """スキップ選択のテスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_input.return_value = "s"

        result = prompt_user_action("test_repo", ["未コミットの変更があります"])

        assert result == "s"

        captured = capsys.readouterr()
        assert "test_repo に未保存の変更があります" in captured.out
        assert "未コミットの変更があります" in captured.out

    @pytest.mark.unit
    @patch("builtins.input")
    def test_prompt_user_action_continue(self, mock_input):
        """続行選択のテスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_input.return_value = "c"

        result = prompt_user_action("test_repo", ["stashがあります"])

        assert result == "c"

    @pytest.mark.unit
    @patch("builtins.input")
    def test_prompt_user_action_quit(self, mock_input):
        """終了選択のテスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_input.return_value = "q"

        result = prompt_user_action("test_repo", ["未pushのコミットがあります"])

        assert result == "q"

    @pytest.mark.unit
    @patch("builtins.input")
    def test_prompt_user_action_invalid_then_valid(self, mock_input, capsys):
        """無効な入力後に有効な入力のテスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_input.side_effect = ["x", "invalid", "s"]

        result = prompt_user_action("test_repo", ["問題"])

        assert result == "s"

        captured = capsys.readouterr()
        assert "s, c, q のいずれかを入力してください" in captured.out

    @pytest.mark.unit
    @patch("builtins.input")
    def test_prompt_user_action_case_insensitive(self, mock_input):
        """大文字小文字を区別しないテスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_input.return_value = "S"

        result = prompt_user_action("test_repo", ["問題"])

        assert result == "s"

    @pytest.mark.unit
    @patch("builtins.input")
    def test_prompt_user_action_multiple_issues(self, mock_input, capsys):
        """複数の問題がある場合のテスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_input.return_value = "c"

        issues = ["未コミットの変更があります", "未pushのコミットがあります", "stashがあります"]

        result = prompt_user_action("test_repo", issues)

        assert result == "c"

        captured = capsys.readouterr()
        for issue in issues:
            assert issue in captured.out


class TestCreateEmergencyBackup:
    """create_emergency_backup関数のテスト"""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """テスト用リポジトリディレクトリ"""
        repo = tmp_path / "test_repo"
        repo.mkdir()
        # テスト用ファイルを作成
        (repo / "test_file.txt").write_text("test content", encoding="utf-8")
        return repo

    @pytest.mark.unit
    @patch("time.time")
    def test_create_emergency_backup_success(self, mock_time, temp_repo, capsys):
        """緊急バックアップ作成成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_time.return_value = 1234567890

        result = create_emergency_backup(temp_repo)

        assert result is True

        # バックアップディレクトリが作成されていることを確認
        backup_name = "test_repo.backup.1234567890"
        backup_path = temp_repo.parent / backup_name
        assert backup_path.exists()
        assert (backup_path / "test_file.txt").exists()

        captured = capsys.readouterr()
        assert "緊急バックアップ作成" in captured.out
        assert backup_name in captured.out

    @pytest.mark.unit
    @patch("shutil.copytree")
    def test_create_emergency_backup_failure(self, mock_copytree, temp_repo, capsys):
        """緊急バックアップ作成失敗テスト"""
        verify_current_platform()  # プラットフォーム検証

        mock_copytree.side_effect = OSError("Permission denied")

        result = create_emergency_backup(temp_repo)

        assert result is False

        captured = capsys.readouterr()
        assert "バックアップ失敗" in captured.out

    @pytest.mark.unit
    def test_create_emergency_backup_nonexistent_repo(self, tmp_path, capsys):
        """存在しないリポジトリのバックアップテスト"""
        verify_current_platform()  # プラットフォーム検証

        nonexistent_repo = tmp_path / "nonexistent"

        result = create_emergency_backup(nonexistent_repo)

        assert result is False

        captured = capsys.readouterr()
        assert "バックアップ失敗" in captured.out

    @pytest.mark.unit
    @patch("time.time")
    def test_create_emergency_backup_unique_names(self, mock_time, temp_repo):
        """バックアップ名の一意性テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 異なるタイムスタンプでテスト
        mock_time.side_effect = [1234567890, 1234567891]

        result1 = create_emergency_backup(temp_repo)
        result2 = create_emergency_backup(temp_repo)

        assert result1 is True
        assert result2 is True

        # 異なる名前のバックアップが作成されることを確認
        backup1 = temp_repo.parent / "test_repo.backup.1234567890"
        backup2 = temp_repo.parent / "test_repo.backup.1234567891"

        assert backup1.exists()
        assert backup2.exists()


class TestSafetyCheckIntegration:
    """セキュリティチェックの統合テスト"""

    @pytest.mark.unit
    @patch("subprocess.run")
    @patch("builtins.input")
    def test_full_safety_workflow(self, mock_input, mock_run, tmp_path, capsys):
        """完全なセーフティワークフローテスト"""
        verify_current_platform()  # プラットフォーム検証

        # テストリポジトリを作成
        repo = tmp_path / "test_repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        (repo / "test_file.py").write_text("print('hello')", encoding="utf-8")

        # 未コミットの変更があることをモック
        mock_run.return_value = Mock(returncode=0, stdout="M  test_file.py\n", stderr="")

        # ユーザーがスキップを選択
        mock_input.return_value = "s"

        # チェック実行
        has_issues, issues = check_unpushed_changes(repo)

        assert has_issues is True
        assert len(issues) > 0

        # ユーザーアクション
        action = prompt_user_action(repo.name, issues)
        assert action == "s"

    @pytest.mark.unit
    def test_error_handling_robustness(self, tmp_path):
        """エラーハンドリングの堅牢性テスト"""
        verify_current_platform()  # プラットフォーム検証

        # 存在しないパスでのテスト
        nonexistent_path = tmp_path / "nonexistent"

        # 関数がクラッシュしないことを確認
        has_issues, issues = check_unpushed_changes(nonexistent_path)
        assert has_issues is False
        assert issues == []

        # バックアップ作成も失敗するが例外は発生しない
        result = create_emergency_backup(nonexistent_path)
        assert result is False

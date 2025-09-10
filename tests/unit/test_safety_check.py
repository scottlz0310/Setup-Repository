"""安全性検証のテスト"""

import shutil
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.setup_repo.safety_check import (
    check_unpushed_changes,
    create_emergency_backup,
    prompt_user_action,
)


class TestCheckUnpushedChanges:
    """check_unpushed_changes関数のテスト"""

    def test_check_unpushed_changes_not_git_repo(self):
        """Gitリポジトリでない場合のテスト"""
        # Arrange
        repo_path = Path("/test/not_git_repo")

        # Act
        with patch("pathlib.Path.exists", return_value=False):
            has_issues, issues = check_unpushed_changes(repo_path)

        # Assert
        assert has_issues is False
        assert issues == []

    @patch("subprocess.run")
    def test_check_unpushed_changes_no_issues(self, mock_run):
        """問題がない場合のテスト"""
        # Arrange
        repo_path = Path("/test/clean_repo")
        mock_run.side_effect = [
            Mock(stdout="", returncode=0),  # git status --porcelain
            Mock(stdout="", returncode=0),  # git log @{u}..HEAD
            Mock(stdout="", returncode=0),  # git stash list
        ]

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            has_issues, issues = check_unpushed_changes(repo_path)

        # Assert
        assert has_issues is False
        assert issues == []
        assert mock_run.call_count == 3

    @patch("subprocess.run")
    def test_check_unpushed_changes_uncommitted_changes(self, mock_run):
        """未コミットの変更がある場合のテスト"""
        # Arrange
        repo_path = Path("/test/dirty_repo")
        mock_run.side_effect = [
            Mock(stdout="M  file.txt\n", returncode=0),  # git status --porcelain
            Mock(stdout="", returncode=0),  # git log @{u}..HEAD
            Mock(stdout="", returncode=0),  # git stash list
        ]

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            has_issues, issues = check_unpushed_changes(repo_path)

        # Assert
        assert has_issues is True
        assert "未コミットの変更があります" in issues
        assert len(issues) == 1

    @patch("subprocess.run")
    def test_check_unpushed_changes_unpushed_commits(self, mock_run):
        """未pushのコミットがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/unpushed_repo")
        mock_run.side_effect = [
            Mock(stdout="", returncode=0),  # git status --porcelain
            Mock(stdout="abc123 commit message\n", returncode=0),  # git log @{u}..HEAD
            Mock(stdout="", returncode=0),  # git stash list
        ]

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            has_issues, issues = check_unpushed_changes(repo_path)

        # Assert
        assert has_issues is True
        assert "未pushのコミットがあります" in issues
        assert len(issues) == 1

    @patch("subprocess.run")
    def test_check_unpushed_changes_stash_exists(self, mock_run):
        """stashがある場合のテスト"""
        # Arrange
        repo_path = Path("/test/stashed_repo")
        mock_run.side_effect = [
            Mock(stdout="", returncode=0),  # git status --porcelain
            Mock(stdout="", returncode=0),  # git log @{u}..HEAD
            Mock(stdout="stash@{0}: WIP on main\n", returncode=0),  # git stash list
        ]

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            has_issues, issues = check_unpushed_changes(repo_path)

        # Assert
        assert has_issues is True
        assert "stashがあります" in issues
        assert len(issues) == 1

    @patch("subprocess.run")
    def test_check_unpushed_changes_multiple_issues(self, mock_run):
        """複数の問題がある場合のテスト"""
        # Arrange
        repo_path = Path("/test/messy_repo")
        mock_run.side_effect = [
            Mock(stdout="M  file.txt\n", returncode=0),  # git status --porcelain
            Mock(stdout="abc123 commit message\n", returncode=0),  # git log @{u}..HEAD
            Mock(stdout="stash@{0}: WIP on main\n", returncode=0),  # git stash list
        ]

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            has_issues, issues = check_unpushed_changes(repo_path)

        # Assert
        assert has_issues is True
        assert len(issues) == 3
        assert "未コミットの変更があります" in issues
        assert "未pushのコミットがあります" in issues
        assert "stashがあります" in issues

    @patch("subprocess.run")
    def test_check_unpushed_changes_git_command_error(self, mock_run):
        """Gitコマンドエラーの場合のテスト"""
        # Arrange
        repo_path = Path("/test/error_repo")
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            has_issues, issues = check_unpushed_changes(repo_path)

        # Assert
        assert has_issues is False
        assert issues == []

    @patch("subprocess.run")
    def test_check_unpushed_changes_log_command_no_upstream(self, mock_run):
        """上流ブランチがない場合のテスト"""
        # Arrange
        repo_path = Path("/test/no_upstream_repo")
        mock_run.side_effect = [
            Mock(stdout="", returncode=0),  # git status --porcelain
            Mock(stdout="", returncode=128),  # git log @{u}..HEAD (no upstream)
            Mock(stdout="", returncode=0),  # git stash list
        ]

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            has_issues, issues = check_unpushed_changes(repo_path)

        # Assert
        assert has_issues is False
        assert issues == []


class TestPromptUserAction:
    """prompt_user_action関数のテスト"""

    @patch("builtins.input")
    @patch("builtins.print")
    def test_prompt_user_action_skip(self, mock_print, mock_input):
        """スキップ選択のテスト"""
        # Arrange
        repo_name = "test_repo"
        issues = ["未コミットの変更があります", "stashがあります"]
        mock_input.return_value = "s"

        # Act
        result = prompt_user_action(repo_name, issues)

        # Assert
        assert result == "s"
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("test_repo に未保存の変更があります" in call for call in print_calls)
        assert any("未コミットの変更があります" in call for call in print_calls)
        assert any("stashがあります" in call for call in print_calls)

    @patch("builtins.input")
    @patch("builtins.print")
    def test_prompt_user_action_continue(self, mock_print, mock_input):
        """続行選択のテスト"""
        # Arrange
        repo_name = "test_repo"
        issues = ["未pushのコミットがあります"]
        mock_input.return_value = "c"

        # Act
        result = prompt_user_action(repo_name, issues)

        # Assert
        assert result == "c"

    @patch("builtins.input")
    @patch("builtins.print")
    def test_prompt_user_action_quit(self, mock_print, mock_input):
        """終了選択のテスト"""
        # Arrange
        repo_name = "test_repo"
        issues = ["未コミットの変更があります"]
        mock_input.return_value = "q"

        # Act
        result = prompt_user_action(repo_name, issues)

        # Assert
        assert result == "q"

    @patch("builtins.input")
    @patch("builtins.print")
    def test_prompt_user_action_invalid_then_valid(self, mock_print, mock_input):
        """無効な入力後に有効な入力のテスト"""
        # Arrange
        repo_name = "test_repo"
        issues = ["未コミットの変更があります"]
        mock_input.side_effect = ["x", "invalid", "s"]

        # Act
        result = prompt_user_action(repo_name, issues)

        # Assert
        assert result == "s"
        assert mock_input.call_count == 3
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        # 無効な入力に対するメッセージが表示されることを確認
        assert any("s, c, q のいずれかを入力してください" in call for call in print_calls)

    @patch("builtins.input")
    @patch("builtins.print")
    def test_prompt_user_action_uppercase_input(self, mock_print, mock_input):
        """大文字入力のテスト"""
        # Arrange
        repo_name = "test_repo"
        issues = ["未コミットの変更があります"]
        mock_input.return_value = "S"

        # Act
        result = prompt_user_action(repo_name, issues)

        # Assert
        assert result == "s"  # 小文字に変換される

    @patch("builtins.input")
    @patch("builtins.print")
    def test_prompt_user_action_whitespace_input(self, mock_print, mock_input):
        """空白を含む入力のテスト"""
        # Arrange
        repo_name = "test_repo"
        issues = ["未コミットの変更があります"]
        mock_input.return_value = "  c  "

        # Act
        result = prompt_user_action(repo_name, issues)

        # Assert
        assert result == "c"  # 空白が除去される


class TestCreateEmergencyBackup:
    """create_emergency_backup関数のテスト"""

    @patch("shutil.copytree")
    @patch("builtins.print")
    @patch("time.time")
    def test_create_emergency_backup_success(self, mock_time, mock_print, mock_copytree):
        """バックアップ作成成功のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_time.return_value = 1234567890
        mock_copytree.return_value = None

        # Act
        result = create_emergency_backup(repo_path)

        # Assert
        assert result is True
        expected_backup_path = Path("/test/repo.backup.1234567890")
        mock_copytree.assert_called_once_with(repo_path, expected_backup_path)
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("緊急バックアップ作成: repo.backup.1234567890" in call for call in print_calls)

    @patch("shutil.copytree")
    @patch("builtins.print")
    @patch("time.time")
    def test_create_emergency_backup_failure(self, mock_time, mock_print, mock_copytree):
        """バックアップ作成失敗のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_time.return_value = 1234567890
        mock_copytree.side_effect = OSError("Permission denied")

        # Act
        result = create_emergency_backup(repo_path)

        # Assert
        assert result is False
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("バックアップ失敗: Permission denied" in call for call in print_calls)

    @patch("shutil.copytree")
    @patch("builtins.print")
    @patch("time.time")
    def test_create_emergency_backup_different_repo_names(self, mock_time, mock_print, mock_copytree):
        """異なるリポジトリ名でのバックアップのテスト"""
        # Arrange
        repo_paths = [
            Path("/test/my-awesome-repo"),
            Path("/test/simple_repo"),
            Path("/test/repo.with.dots"),
        ]
        mock_time.return_value = 9876543210
        mock_copytree.return_value = None

        for repo_path in repo_paths:
            # Act
            result = create_emergency_backup(repo_path)

            # Assert
            assert result is True
            expected_backup_name = f"{repo_path.name}.backup.9876543210"
            expected_backup_path = repo_path.parent / expected_backup_name
            mock_copytree.assert_called_with(repo_path, expected_backup_path)

    @patch("shutil.copytree")
    @patch("builtins.print")
    @patch("time.time")
    def test_create_emergency_backup_exception_handling(self, mock_time, mock_print, mock_copytree):
        """例外処理のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_time.return_value = 1234567890
        mock_copytree.side_effect = Exception("Unexpected error")

        # Act
        result = create_emergency_backup(repo_path)

        # Assert
        assert result is False
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("バックアップ失敗: Unexpected error" in call for call in print_calls)


class TestSafetyCheckEdgeCases:
    """安全性チェックのエッジケースのテスト"""

    @patch("subprocess.run")
    def test_check_unpushed_changes_with_path_object(self, mock_run):
        """Pathオブジェクトでの動作確認テスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_run.side_effect = [
            Mock(stdout="", returncode=0),  # git status --porcelain
            Mock(stdout="", returncode=0),  # git log @{u}..HEAD
            Mock(stdout="", returncode=0),  # git stash list
        ]

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            has_issues, issues = check_unpushed_changes(repo_path)

        # Assert
        assert has_issues is False
        assert issues == []
        # cwdパラメータにPathオブジェクトが渡されることを確認
        for call in mock_run.call_args_list:
            assert call[1]["cwd"] == repo_path

    @patch("builtins.input")
    @patch("builtins.print")
    def test_prompt_user_action_empty_issues_list(self, mock_print, mock_input):
        """空の問題リストでのテスト"""
        # Arrange
        repo_name = "test_repo"
        issues = []
        mock_input.return_value = "s"

        # Act
        result = prompt_user_action(repo_name, issues)

        # Assert
        assert result == "s"
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("test_repo に未保存の変更があります" in call for call in print_calls)

    @patch("shutil.copytree")
    @patch("builtins.print")
    def test_create_emergency_backup_time_import_in_function(self, mock_print, mock_copytree):
        """関数内でのtime.timeインポートのテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_copytree.return_value = None

        # Act
        with patch("time.time", return_value=1111111111):
            result = create_emergency_backup(repo_path)

        # Assert
        assert result is True
        expected_backup_path = Path("/test/repo.backup.1111111111")
        mock_copytree.assert_called_once_with(repo_path, expected_backup_path)
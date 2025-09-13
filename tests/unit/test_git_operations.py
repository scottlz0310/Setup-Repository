"""
Git操作機能のテスト

マルチプラットフォームテスト方針に準拠したGit操作機能のテスト
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from setup_repo.git_operations import (
    GitError,
    GitOperations,
    check_git_status,
    clone_repository,
    commit_changes,
    create_branch,
    push_changes,
    switch_branch,
)
from tests.multiplatform.helpers import (
    get_platform_specific_config,
    verify_current_platform,
)


class TestGitOperations:
    """Git操作機能のテスト"""

    def test_check_git_status_clean(self):
        """クリーンなGitステータスのテスト"""
        verify_current_platform()  # プラットフォーム検証

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            result = check_git_status("/test/repo")
            assert result["clean"] is True
            assert len(result["modified"]) == 0
            assert len(result["untracked"]) == 0

    def test_check_git_status_with_changes(self):
        """変更があるGitステータスのテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=" M modified_file.py\n?? untracked_file.py\n A  added_file.py", stderr=""
            )

            result = check_git_status("/test/repo")
            assert result["clean"] is False
            assert "modified_file.py" in result["modified"]
            assert "untracked_file.py" in result["untracked"]
            assert "added_file.py" in result["staged"]

    def test_check_git_status_not_git_repo(self):
        """Gitリポジトリでない場合のテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=128, stderr="fatal: not a git repository")

            with pytest.raises(GitError, match="Gitリポジトリではありません"):
                check_git_status("/not/git/repo")

    def test_clone_repository_success(self):
        """リポジトリクローン成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Cloning...")

            result = clone_repository("https://github.com/user/repo.git", "/test/destination")

            assert result["success"] is True
            assert result["path"] == "/test/destination"

    def test_clone_repository_failure(self):
        """リポジトリクローン失敗テスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="fatal: repository not found")

            with pytest.raises(GitError, match="クローンに失敗"):
                clone_repository("https://github.com/user/nonexistent.git", "/test/destination")

    def test_commit_changes_success(self):
        """変更のコミット成功テスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="[main 1234567] Test commit")

            result = commit_changes("/test/repo", "Test commit message")
            assert result["success"] is True
            assert "1234567" in result["commit_hash"]

    def test_commit_changes_no_changes(self):
        """コミットする変更がない場合のテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="nothing to commit, working tree clean")

            result = commit_changes("/test/repo", "Test commit")
            assert result["success"] is False
            assert result["reason"] == "no_changes"

    def test_push_changes_success(self):
        """変更のプッシュ成功テスト"""
        verify_current_platform()  # プラットフォーム検証

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="To github.com:user/repo.git")

            result = push_changes("/test/repo", "main")
            assert result["success"] is True

    def test_push_changes_authentication_failure(self):
        """認証失敗によるプッシュエラーテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=128, stderr="fatal: Authentication failed")

            with pytest.raises(GitError, match="認証に失敗"):
                push_changes("/test/repo", "main")

    def test_create_branch_success(self):
        """ブランチ作成成功テスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            result = create_branch("/test/repo", "feature/new-feature")
            assert result["success"] is True
            assert result["branch"] == "feature/new-feature"

    def test_create_branch_already_exists(self):
        """既存ブランチ作成エラーテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=128, stderr="fatal: A branch named 'main' already exists")

            with pytest.raises(GitError, match="ブランチが既に存在"):
                create_branch("/test/repo", "main")

    def test_switch_branch_success(self):
        """ブランチ切り替え成功テスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Switched to branch 'develop'")

            result = switch_branch("/test/repo", "develop")
            assert result["success"] is True
            assert result["current_branch"] == "develop"

    def test_switch_branch_not_exists(self):
        """存在しないブランチへの切り替えエラーテスト"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="error: pathspec 'nonexistent' did not match")

            with pytest.raises(GitError, match="ブランチが見つかりません"):
                switch_branch("/test/repo", "nonexistent")

    def test_git_operations_class_init(self):
        """GitOperationsクラスの初期化テスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)
            assert git_ops.repo_path == Path(temp_dir)
            assert git_ops.platform == platform_info.name

    def test_git_operations_add_files(self):
        """ファイル追加操作のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                result = git_ops.add_files(["file1.py", "file2.py"])
                assert result["success"] is True
                assert len(result["added_files"]) == 2

    def test_git_operations_get_current_branch(self):
        """現在のブランチ取得テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="main")

                branch = git_ops.get_current_branch()
                assert branch == "main"

    def test_git_operations_get_remote_url(self):
        """リモートURL取得テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="https://github.com/user/repo.git")

                url = git_ops.get_remote_url()
                assert url == "https://github.com/user/repo.git"

    def test_git_operations_get_commit_history(self):
        """コミット履歴取得テスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="1234567 Initial commit\n8901234 Second commit")

                history = git_ops.get_commit_history(limit=2)
                assert len(history) == 2
                assert history[0]["hash"] == "1234567"
                assert history[0]["message"] == "Initial commit"

    @pytest.mark.integration
    def test_git_operations_full_workflow(self):
        """Git操作の完全ワークフローテスト"""
        verify_current_platform()  # プラットフォーム検証

        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)

            with patch("subprocess.run") as mock_run:
                # 各Git操作が成功することをモック
                mock_run.return_value = Mock(returncode=0, stdout="success")

                # ワークフロー実行
                git_ops.add_files(["test.py"])
                commit_result = git_ops.commit("Test commit")
                push_result = git_ops.push()

                assert commit_result["success"] is True
                assert push_result["success"] is True

    def test_git_operations_error_handling(self):
        """Git操作のエラーハンドリングテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)

            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("git command not found")

                with pytest.raises(GitError, match="Gitコマンドが見つかりません"):
                    git_ops.get_current_branch()

    @pytest.mark.slow
    def test_git_operations_performance(self):
        """Git操作のパフォーマンステスト"""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            git_ops = GitOperations(temp_dir)

            start_time = time.time()

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="test")

                # 複数のGit操作を実行
                for _ in range(10):
                    git_ops.get_current_branch()
                    git_ops.check_status()

            elapsed = time.time() - start_time
            assert elapsed < 3.0, f"Git操作が遅すぎます: {elapsed}秒"

    def test_git_operations_platform_specific_paths(self):
        """プラットフォーム固有のパス処理テスト"""
        verify_current_platform()  # プラットフォーム検証
        get_platform_specific_config()  # プラットフォーム設定取得

        if platform_info.name == "windows":
            test_path = "C:\\Users\\test\\repo"
        else:
            test_path = "/home/test/repo"

        git_ops = GitOperations(test_path)
        assert str(git_ops.repo_path) == test_path

"""Git操作モジュールのテスト"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from src.setup_repo.git_operations import (
    GitOperations,
    _auto_pop_stash,
    _auto_stash_changes,
    _clone_repository,
    _sync_repository_once,
    _update_repository,
    choose_clone_url,
    create_git_operations,
    sync_repository,
    sync_repository_with_retries,
)


class TestGitOperations:
    """GitOperationsクラスのテスト"""

    def test_init_with_config(self):
        """設定付き初期化のテスト"""
        # Arrange
        config = {"use_https": True, "max_retries": 3}

        # Act
        git_ops = GitOperations(config)

        # Assert
        assert git_ops.config == config

    def test_init_without_config(self):
        """設定なし初期化のテスト"""
        # Act
        git_ops = GitOperations()

        # Assert
        assert git_ops.config == {}

    def test_init_with_none_config(self):
        """None設定での初期化のテスト"""
        # Act
        git_ops = GitOperations(None)

        # Assert
        assert git_ops.config == {}

    def test_is_git_repository_true(self):
        """Gitリポジトリ判定（True）のテスト"""
        # Arrange
        git_ops = GitOperations()

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            result = git_ops.is_git_repository("/test/repo")

        # Assert
        assert result is True

    def test_is_git_repository_false(self):
        """Gitリポジトリ判定（False）のテスト"""
        # Arrange
        git_ops = GitOperations()

        # Act
        with patch("pathlib.Path.exists", return_value=False):
            result = git_ops.is_git_repository("/test/not_repo")

        # Assert
        assert result is False

    def test_is_git_repository_with_path_object(self):
        """Pathオブジェクトでのリポジトリ判定のテスト"""
        # Arrange
        git_ops = GitOperations()
        test_path = Path("/test/repo")

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            result = git_ops.is_git_repository(test_path)

        # Assert
        assert result is True

    @patch("subprocess.run")
    def test_clone_repository_success(self, mock_run):
        """リポジトリクローン成功のテスト"""
        # Arrange
        git_ops = GitOperations()
        mock_run.return_value = Mock()

        # Act
        result = git_ops.clone_repository(
            "https://github.com/user/repo.git", "/test/dest"
        )

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["git", "clone", "https://github.com/user/repo.git", "/test/dest"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_clone_repository_failure(self, mock_run):
        """リポジトリクローン失敗のテスト"""
        # Arrange
        git_ops = GitOperations()
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Act
        result = git_ops.clone_repository(
            "https://github.com/user/repo.git", "/test/dest"
        )

        # Assert
        assert result is False

    @patch("subprocess.run")
    def test_clone_repository_with_path_object(self, mock_run):
        """Pathオブジェクトでのクローンのテスト"""
        # Arrange
        git_ops = GitOperations()
        mock_run.return_value = Mock()
        dest_path = Path("/test/dest")

        # Act
        result = git_ops.clone_repository("https://github.com/user/repo.git", dest_path)

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["git", "clone", "https://github.com/user/repo.git", str(dest_path)],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_pull_repository_success(self, mock_run):
        """リポジトリpull成功のテスト"""
        # Arrange
        git_ops = GitOperations()
        mock_run.return_value = Mock()

        # Act
        result = git_ops.pull_repository("/test/repo")

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["git", "pull", "--rebase"],
            cwd=Path("/test/repo"),
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_pull_repository_failure(self, mock_run):
        """リポジトリpull失敗のテスト"""
        # Arrange
        git_ops = GitOperations()
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Act
        result = git_ops.pull_repository("/test/repo")

        # Assert
        assert result is False

    @patch("subprocess.run")
    def test_pull_repository_with_path_object(self, mock_run):
        """Pathオブジェクトでのpullのテスト"""
        # Arrange
        git_ops = GitOperations()
        mock_run.return_value = Mock()
        repo_path = Path("/test/repo")

        # Act
        result = git_ops.pull_repository(repo_path)

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["git", "pull", "--rebase"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )


class TestChooseCloneUrl:
    """choose_clone_url関数のテスト"""

    def test_choose_clone_url_https_forced(self):
        """HTTPS強制時のテスト"""
        # Arrange
        repo = {
            "clone_url": "https://github.com/user/repo.git",
            "ssh_url": "git@github.com:user/repo.git",
            "full_name": "user/repo",
        }

        # Act
        result = choose_clone_url(repo, use_https=True)

        # Assert
        assert result == "https://github.com/user/repo.git"

    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    def test_choose_clone_url_ssh_available(self, mock_run, mock_exists):
        """SSH利用可能時のテスト"""
        # Arrange
        repo = {
            "clone_url": "https://github.com/user/repo.git",
            "ssh_url": "git@github.com:user/repo.git",
            "full_name": "user/repo",
        }
        mock_exists.return_value = True  # SSH鍵が存在
        mock_run.return_value = Mock(returncode=1)  # SSH接続成功

        # Act
        result = choose_clone_url(repo, use_https=False)

        # Assert
        assert result == "git@github.com:user/repo.git"

    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    def test_choose_clone_url_ssh_connection_success(self, mock_run, mock_exists):
        """SSH接続成功時のテスト"""
        # Arrange
        repo = {
            "clone_url": "https://github.com/user/repo.git",
            "ssh_url": "git@github.com:user/repo.git",
            "full_name": "user/repo",
        }
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=0)  # SSH接続完全成功

        # Act
        result = choose_clone_url(repo, use_https=False)

        # Assert
        assert result == "git@github.com:user/repo.git"

    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    def test_choose_clone_url_ssh_timeout(self, mock_run, mock_exists):
        """SSHタイムアウト時のテスト"""
        # Arrange
        repo = {
            "clone_url": "https://github.com/user/repo.git",
            "ssh_url": "git@github.com:user/repo.git",
            "full_name": "user/repo",
        }
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired("ssh", 5)

        # Act
        result = choose_clone_url(repo, use_https=False)

        # Assert
        assert result == "https://github.com/user/repo.git"  # HTTPSにフォールバック

    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    def test_choose_clone_url_ssh_error(self, mock_run, mock_exists):
        """SSH接続エラー時のテスト"""
        # Arrange
        repo = {
            "clone_url": "https://github.com/user/repo.git",
            "ssh_url": "git@github.com:user/repo.git",
            "full_name": "user/repo",
        }
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(255, "ssh")

        # Act
        result = choose_clone_url(repo, use_https=False)

        # Assert
        assert result == "https://github.com/user/repo.git"  # HTTPSにフォールバック

    @patch("pathlib.Path.exists")
    def test_choose_clone_url_no_ssh_keys(self, mock_exists):
        """SSH鍵が存在しない時のテスト"""
        # Arrange
        repo = {
            "clone_url": "https://github.com/user/repo.git",
            "ssh_url": "git@github.com:user/repo.git",
            "full_name": "user/repo",
        }
        mock_exists.return_value = False  # SSH鍵が存在しない

        # Act
        result = choose_clone_url(repo, use_https=False)

        # Assert
        assert result == "https://github.com/user/repo.git"  # HTTPSにフォールバック

    @patch("pathlib.Path.exists")
    @patch("subprocess.run")
    def test_choose_clone_url_ssh_failure_returncode(self, mock_run, mock_exists):
        """SSH接続失敗（不正なreturncode）時のテスト"""
        # Arrange
        repo = {
            "clone_url": "https://github.com/user/repo.git",
            "ssh_url": "git@github.com:user/repo.git",
            "full_name": "user/repo",
        }
        mock_exists.return_value = True
        mock_run.return_value = Mock(returncode=255)  # SSH接続失敗

        # Act
        result = choose_clone_url(repo, use_https=False)

        # Assert
        assert result == "https://github.com/user/repo.git"  # HTTPSにフォールバック

    def test_choose_clone_url_no_ssh_url_in_repo(self):
        """リポジトリ情報にssh_urlがない場合のテスト"""
        # Arrange
        repo = {
            "clone_url": "https://github.com/user/repo.git",
            "full_name": "user/repo",
        }

        # Act
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("subprocess.run", return_value=Mock(returncode=1)),
        ):
            result = choose_clone_url(repo, use_https=False)

        # Assert
        assert result == "git@github.com:user/repo.git"  # full_nameから生成


class TestSyncRepository:
    """sync_repository関数のテスト"""

    @patch("src.setup_repo.git_operations._sync_repository_once")
    def test_sync_repository_success(self, mock_sync_once):
        """sync_repository成功のテスト"""
        # Arrange
        repo = {"name": "test_repo"}
        dest_dir = Path("/test/dest")
        mock_sync_once.return_value = True

        # Act
        result = sync_repository(repo, dest_dir, dry_run=True)

        # Assert
        assert result is True
        mock_sync_once.assert_called_once_with(repo, dest_dir, {"dry_run": True})

    @patch("src.setup_repo.git_operations._sync_repository_once")
    def test_sync_repository_failure(self, mock_sync_once):
        """sync_repository失敗のテスト"""
        # Arrange
        repo = {"name": "test_repo"}
        dest_dir = Path("/test/dest")
        mock_sync_once.return_value = False

        # Act
        result = sync_repository(repo, dest_dir, dry_run=False)

        # Assert
        assert result is False
        mock_sync_once.assert_called_once_with(repo, dest_dir, {"dry_run": False})


class TestSyncRepositoryWithRetries:
    """sync_repository_with_retries関数のテスト"""

    @patch("src.setup_repo.git_operations._sync_repository_once")
    @patch("builtins.print")
    def test_sync_repository_with_retries_success_first_try(
        self, mock_print, mock_sync_once
    ):
        """初回試行で成功のテスト"""
        # Arrange
        repo = {"name": "test_repo"}
        dest_dir = Path("/test/dest")
        config = {"max_retries": 3}
        mock_sync_once.return_value = True

        # Act
        result = sync_repository_with_retries(repo, dest_dir, config)

        # Assert
        assert result is True
        mock_sync_once.assert_called_once()

    @patch("src.setup_repo.git_operations._sync_repository_once")
    @patch("shutil.rmtree")
    @patch("time.sleep")
    @patch("builtins.print")
    def test_sync_repository_with_retries_success_second_try(
        self, mock_print, mock_sleep, mock_rmtree, mock_sync_once
    ):
        """2回目の試行で成功のテスト"""
        # Arrange
        repo = {"name": "test_repo"}
        dest_dir = Path("/test/dest")
        config = {"max_retries": 3}
        mock_sync_once.side_effect = [False, True]  # 1回目失敗、2回目成功

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            result = sync_repository_with_retries(repo, dest_dir, config)

        # Assert
        assert result is True
        assert mock_sync_once.call_count == 2
        mock_rmtree.assert_called_once()
        mock_sleep.assert_called_once_with(1)

    @patch("src.setup_repo.git_operations._sync_repository_once")
    @patch("shutil.rmtree")
    @patch("time.sleep")
    @patch("builtins.print")
    def test_sync_repository_with_retries_all_fail(
        self, mock_print, mock_sleep, mock_rmtree, mock_sync_once
    ):
        """全ての試行が失敗のテスト"""
        # Arrange
        repo = {"name": "test_repo"}
        dest_dir = Path("/test/dest")
        config = {"max_retries": 2}
        mock_sync_once.return_value = False

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            result = sync_repository_with_retries(repo, dest_dir, config)

        # Assert
        assert result is False
        assert mock_sync_once.call_count == 2
        assert mock_rmtree.call_count == 1  # 最後の試行後はrmtreeしない
        mock_sleep.assert_called_once_with(1)

    @patch("src.setup_repo.git_operations._sync_repository_once")
    @patch("builtins.print")
    def test_sync_repository_with_retries_default_max_retries(
        self, mock_print, mock_sync_once
    ):
        """デフォルトのmax_retriesのテスト"""
        # Arrange
        repo = {"name": "test_repo"}
        dest_dir = Path("/test/dest")
        config = {}  # max_retriesが未設定
        mock_sync_once.return_value = False

        # Act
        with patch("pathlib.Path.exists", return_value=False):
            result = sync_repository_with_retries(repo, dest_dir, config)

        # Assert
        assert result is False
        assert mock_sync_once.call_count == 2  # デフォルトは2回

    @patch("src.setup_repo.git_operations._sync_repository_once")
    @patch("shutil.rmtree")
    @patch("time.sleep")
    @patch("builtins.print")
    def test_sync_repository_with_retries_dry_run_no_rmtree(
        self, mock_print, mock_sleep, mock_rmtree, mock_sync_once
    ):
        """ドライランモード時はrmtreeしないテスト"""
        # Arrange
        repo = {"name": "test_repo"}
        dest_dir = Path("/test/dest")
        config = {"max_retries": 2, "dry_run": True}
        mock_sync_once.return_value = False

        # Act
        with patch("pathlib.Path.exists", return_value=True):
            result = sync_repository_with_retries(repo, dest_dir, config)

        # Assert
        assert result is False
        mock_rmtree.assert_not_called()  # ドライランモードではrmtreeしない


class TestSyncRepositoryOnce:
    """_sync_repository_once関数のテスト"""

    @patch("src.setup_repo.git_operations._update_repository")
    @patch("pathlib.Path.exists")
    def test_sync_repository_once_existing_repo(self, mock_exists, mock_update):
        """既存リポジトリの場合のテスト"""
        # Arrange
        repo = {
            "name": "test_repo",
            "clone_url": "https://github.com/user/test_repo.git",
            "full_name": "user/test_repo",
        }
        dest_dir = Path("/test/dest")
        config = {}
        mock_exists.return_value = True
        mock_update.return_value = True

        # Act
        result = _sync_repository_once(repo, dest_dir, config)

        # Assert
        assert result is True
        mock_update.assert_called_once_with("test_repo", dest_dir / "test_repo", config)

    @patch("src.setup_repo.git_operations._clone_repository")
    @patch("pathlib.Path.exists")
    def test_sync_repository_once_new_repo(self, mock_exists, mock_clone):
        """新規リポジトリの場合のテスト"""
        # Arrange
        repo = {
            "name": "test_repo",
            "clone_url": "https://github.com/user/test_repo.git",
        }
        dest_dir = Path("/test/dest")
        config = {}
        mock_exists.return_value = False
        mock_clone.return_value = True

        # Act
        with patch(
            "src.setup_repo.git_operations.choose_clone_url",
            return_value="https://github.com/user/test_repo.git",
        ):
            result = _sync_repository_once(repo, dest_dir, config)

        # Assert
        assert result is True
        mock_clone.assert_called_once()

    @patch("builtins.print")
    @patch("pathlib.Path.exists")
    def test_sync_repository_once_sync_only_new_repo(self, mock_exists, mock_print):
        """sync_only有効で新規リポジトリの場合のテスト"""
        # Arrange
        repo = {
            "name": "test_repo",
            "clone_url": "https://github.com/user/test_repo.git",
            "full_name": "user/test_repo",
        }
        dest_dir = Path("/test/dest")
        config = {"sync_only": True}
        mock_exists.return_value = False

        # Act
        result = _sync_repository_once(repo, dest_dir, config)

        # Assert
        assert result is True
        # 新規クローンをスキップするメッセージが出力される
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("新規クローンをスキップ" in call for call in print_calls)


class TestUpdateRepository:
    """_update_repository関数のテスト"""

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_update_repository_success(self, mock_print, mock_run):
        """リポジトリ更新成功のテスト"""
        # Arrange
        repo_name = "test_repo"
        repo_path = Path("/test/repo")
        config = {}
        mock_run.return_value = Mock()

        # Act
        result = _update_repository(repo_name, repo_path, config)

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["git", "pull", "--rebase"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("builtins.print")
    def test_update_repository_dry_run(self, mock_print):
        """ド���イランモードでの更新のテスト"""
        # Arrange
        repo_name = "test_repo"
        repo_path = Path("/test/repo")
        config = {"dry_run": True}

        # Act
        result = _update_repository(repo_name, repo_path, config)

        # Assert
        assert result is True
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("更新予定" in call for call in print_calls)

    @patch("src.setup_repo.git_operations._auto_stash_changes")
    @patch("src.setup_repo.git_operations._auto_pop_stash")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_update_repository_with_auto_stash(
        self, mock_print, mock_run, mock_pop_stash, mock_stash_changes
    ):
        """auto_stash有効での更新のテスト"""
        # Arrange
        repo_name = "test_repo"
        repo_path = Path("/test/repo")
        config = {"auto_stash": True}
        mock_stash_changes.return_value = True
        mock_run.return_value = Mock()

        # Act
        result = _update_repository(repo_name, repo_path, config)

        # Assert
        assert result is True
        mock_stash_changes.assert_called_once_with(repo_path)
        mock_pop_stash.assert_called_once_with(repo_path)

    @patch("src.setup_repo.git_operations._auto_stash_changes")
    @patch("src.setup_repo.git_operations._auto_pop_stash")
    @patch("subprocess.run")
    @patch("builtins.print")
    def test_update_repository_failure_with_stash(
        self, mock_print, mock_run, mock_pop_stash, mock_stash_changes
    ):
        """stash有りでの更新失敗のテスト"""
        # Arrange
        repo_name = "test_repo"
        repo_path = Path("/test/repo")
        config = {"auto_stash": True}
        mock_stash_changes.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git", stderr="error message"
        )

        # Act
        result = _update_repository(repo_name, repo_path, config)

        # Assert
        assert result is False
        mock_stash_changes.assert_called_once_with(repo_path)
        mock_pop_stash.assert_called_once_with(repo_path)  # エラー時もpopを試行

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_update_repository_failure(self, mock_print, mock_run):
        """リポジトリ更新失敗のテスト"""
        # Arrange
        repo_name = "test_repo"
        repo_path = Path("/test/repo")
        config = {}
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git", stderr="error message"
        )

        # Act
        result = _update_repository(repo_name, repo_path, config)

        # Assert
        assert result is False
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("更新失敗" in call for call in print_calls)


class TestCloneRepository:
    """_clone_repository関数のテスト"""

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_clone_repository_success(self, mock_print, mock_run):
        """リポジトリクローン成功のテスト"""
        # Arrange
        repo_name = "test_repo"
        repo_url = "https://github.com/user/test_repo.git"
        repo_path = Path("/test/repo")
        mock_run.return_value = Mock()

        # Act
        result = _clone_repository(repo_name, repo_url, repo_path, dry_run=False)

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["git", "clone", repo_url, str(repo_path)],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("builtins.print")
    def test_clone_repository_dry_run(self, mock_print):
        """ドライランモードでのクローンのテスト"""
        # Arrange
        repo_name = "test_repo"
        repo_url = "https://github.com/user/test_repo.git"
        repo_path = Path("/test/repo")

        # Act
        result = _clone_repository(repo_name, repo_url, repo_path, dry_run=True)

        # Assert
        assert result is True
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("クローン予定" in call for call in print_calls)

    @patch("subprocess.run")
    @patch("builtins.print")
    def test_clone_repository_failure(self, mock_print, mock_run):
        """リポジトリクローン失敗のテスト"""
        # Arrange
        repo_name = "test_repo"
        repo_url = "https://github.com/user/test_repo.git"
        repo_path = Path("/test/repo")
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git", stderr="error message"
        )

        # Act
        result = _clone_repository(repo_name, repo_url, repo_path, dry_run=False)

        # Assert
        assert result is False
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("クローン失敗" in call for call in print_calls)


class TestAutoStashChanges:
    """_auto_stash_changes関数のテスト"""

    @patch("subprocess.run")
    @patch("time.time")
    def test_auto_stash_changes_with_changes(self, mock_time, mock_run):
        """変更がある場合のstashのテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_time.return_value = 1234567890
        mock_run.side_effect = [
            Mock(stdout="M  file.txt\n"),  # git status
            Mock(),  # git stash
        ]

        # Act
        result = _auto_stash_changes(repo_path)

        # Assert
        assert result is True
        assert mock_run.call_count == 2
        # git status呼び出しの確認
        mock_run.assert_any_call(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        # git stash呼び出しの確認
        mock_run.assert_any_call(
            ["git", "stash", "push", "-u", "-m", "autostash-1234567890"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_auto_stash_changes_no_changes(self, mock_run):
        """変更がない場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_run.return_value = Mock(stdout="")  # 変更なし

        # Act
        result = _auto_stash_changes(repo_path)

        # Assert
        assert result is False
        mock_run.assert_called_once()  # git statusのみ呼び出し

    @patch("subprocess.run")
    def test_auto_stash_changes_git_error(self, mock_run):
        """Git操作エラーの場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Act
        result = _auto_stash_changes(repo_path)

        # Assert
        assert result is False

    @patch("subprocess.run")
    @patch("time.time")
    def test_auto_stash_changes_stash_error(self, mock_time, mock_run):
        """stash操作エラーの場合のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_time.return_value = 1234567890
        mock_run.side_effect = [
            Mock(stdout="M  file.txt\n"),  # git status成功
            subprocess.CalledProcessError(1, "git"),  # git stash失敗
        ]

        # Act
        result = _auto_stash_changes(repo_path)

        # Assert
        assert result is False


class TestAutoPopStash:
    """_auto_pop_stash関数のテスト"""

    @patch("subprocess.run")
    def test_auto_pop_stash_success(self, mock_run):
        """stash pop成功のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_run.return_value = Mock()

        # Act
        result = _auto_pop_stash(repo_path)

        # Assert
        assert result is True
        mock_run.assert_called_once_with(
            ["git", "stash", "pop"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_auto_pop_stash_failure(self, mock_run):
        """stash pop失敗のテスト"""
        # Arrange
        repo_path = Path("/test/repo")
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        # Act
        result = _auto_pop_stash(repo_path)

        # Assert
        assert result is False


class TestCreateGitOperations:
    """create_git_operations関数のテスト"""

    def test_create_git_operations_with_config(self):
        """設定付きでのインスタンス作成のテスト"""
        # Arrange
        config = {"use_https": True}

        # Act
        git_ops = create_git_operations(config)

        # Assert
        assert isinstance(git_ops, GitOperations)
        assert git_ops.config == config

    def test_create_git_operations_without_config(self):
        """設定なしでのインスタンス作成のテスト"""
        # Act
        git_ops = create_git_operations()

        # Assert
        assert isinstance(git_ops, GitOperations)
        assert git_ops.config == {}

    def test_create_git_operations_with_none_config(self):
        """None設定でのインスタンス作成のテスト"""
        # Act
        git_ops = create_git_operations(None)

        # Assert
        assert isinstance(git_ops, GitOperations)
        assert git_ops.config == {}

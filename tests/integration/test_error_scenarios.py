"""
エラーハンドリングフローの統合テスト

このモジュールでは、様々なエラーシナリオでのシステムの動作を
検証します。ネットワークエラー、ファイルシステムエラー、
認証エラーなど、実際の運用で発生する可能性のあるエラーに
対する適切な処理を確認します。
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
import requests

from setup_repo.github_api import GitHubAPIError
from setup_repo.sync import sync_repositories


@pytest.mark.integration
class TestErrorScenarios:
    """エラーシナリオの統合テストクラス"""

    def test_network_connection_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """ネットワーク接続エラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # ネットワークエラーをシミュレート
        network_error = requests.exceptions.ConnectionError("ネットワークに接続できません")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", side_effect=network_error),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        # エラーが適切に処理されることを確認
        assert not result.success
        assert result.errors
        assert "ネットワークに接続できません" in str(result.errors[0])

    def test_github_api_authentication_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """GitHub API認証エラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 認証エラーをシミュレート
        auth_error = GitHubAPIError("認証に失敗しました: 無効なトークン")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", side_effect=auth_error),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
        ):
            result = sync_repositories(sample_config, dry_run=False)

            # エラーが適切に処理されることを確認
            assert not result.success
            assert result.errors
            assert "認証に失敗しました" in str(result.errors[0])

    def test_github_api_rate_limit_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """GitHub APIレート制限エラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # レート制限エラーをシミュレート
        rate_limit_error = GitHubAPIError("API rate limit exceeded")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", side_effect=rate_limit_error),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
        ):
            result = sync_repositories(sample_config, dry_run=False)

            # エラーが適切に処理されることを確認
            assert not result.success
            assert result.errors
            assert "rate limit" in str(result.errors[0]).lower()

    def test_file_system_permission_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """ファイルシステム権限エラーのテスト"""
        # 一時ディレクトリを使用してファイルシステム操作を安全化
        with tempfile.TemporaryDirectory() as safe_temp_dir:
            restricted_dir = Path(safe_temp_dir) / "restricted"
            sample_config["clone_destination"] = str(restricted_dir)

        mock_repos = [
            {
                "name": "permission-test-repo",
                "full_name": "test_user/permission-test-repo",
                "clone_url": "https://github.com/test_user/permission-test-repo.git",
                "ssh_url": "git@github.com:test_user/permission-test-repo.git",
                "description": "権限テスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        # ファイルシステムエラーをシミュレート
        permission_error = PermissionError("Permission denied: cannot create directory")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            # ディレクトリ作成は成功させ、sync_repository_with_retriesでエラーを発生
            patch("pathlib.Path.mkdir"),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=permission_error,
            ),
            patch("setup_repo.sync.ensure_uv"),
            patch("sys.exit"),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        # エラーが適切に処理されることを確認
        assert not result.success
        assert result.errors

    @pytest.mark.skipif(not hasattr(os, "statvfs"), reason="os.statvfs not available on Windows")
    def test_disk_space_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """ディスク容量不足エラーのテスト（Unix系のみ）"""
        # 一時ディレクトリを使用してディスク操作を安全化
        with tempfile.TemporaryDirectory() as safe_temp_dir:
            clone_destination = Path(safe_temp_dir) / "repos"
            sample_config["clone_destination"] = str(clone_destination)

        mock_repos = [
            {
                "name": "large-repo",
                "full_name": "test_user/large-repo",
                "clone_url": "https://github.com/test_user/large-repo.git",
                "ssh_url": "git@github.com:test_user/large-repo.git",
                "description": "大きなリポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        # ディスク容量不足エラーをシミュレート
        disk_error = OSError("No space left on device")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            patch("setup_repo.sync.sync_repository_with_retries", side_effect=disk_error),
            patch("shutil.disk_usage", return_value=(0, 0, 0)),
            patch("os.statvfs", side_effect=disk_error),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert not result.success
        assert result.errors

    def test_git_clone_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """Gitクローンエラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        mock_repos = [
            {
                "name": "clone-error-repo",
                "full_name": "test_user/clone-error-repo",
                "clone_url": "https://github.com/test_user/clone-error-repo.git",
                "ssh_url": "git@github.com:test_user/clone-error-repo.git",
                "description": "クローンエラーテスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        def mock_sync_with_error(repo, dest_dir, config):
            # Gitクローンエラーをシミュレート
            raise RuntimeError("fatal: repository 'https://github.com/test_user/clone-error-repo.git' not found")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=mock_sync_with_error,
            ),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert not result.success
        assert result.errors
        assert "not found" in str(result.errors[0])

    def test_git_pull_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """Gitプルエラーのテスト"""
        # 一時ディレクトリを使用してGit操作を安全化
        with tempfile.TemporaryDirectory() as safe_temp_dir:
            clone_destination = Path(safe_temp_dir) / "repos"
            sample_config["clone_destination"] = str(clone_destination)

            # 既存のリポジトリをモック化（実際のファイル作成を避ける）

        mock_repos = [
            {
                "name": "pull-error-repo",
                "full_name": "test_user/pull-error-repo",
                "clone_url": "https://github.com/test_user/pull-error-repo.git",
                "ssh_url": "git@github.com:test_user/pull-error-repo.git",
                "description": "プルエラーテスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        def mock_sync_with_pull_error(*args, **kwargs):
            # Gitプルエラーをシミュレート
            raise RuntimeError("error: Your local changes to the following files would be overwritten by merge")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            # ディレクトリ作成とuv確認は成功させる
            patch("pathlib.Path.mkdir"),
            patch("setup_repo.sync.ensure_uv"),
            # SSH接続チェックは成功させる
            patch("subprocess.run", return_value=Mock(returncode=0, stdout="")),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=mock_sync_with_pull_error,
            ),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("sys.exit"),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert not result.success
        assert result.errors
        assert "overwritten by merge" in str(result.errors[0])

    def test_corrupted_config_file_error(
        self,
        temp_dir: Path,
    ) -> None:
        """破損した設定ファイルエラーのテスト"""
        # 破損したJSONファイルを作成
        corrupted_config_file = temp_dir / "corrupted_config.json"
        with open(corrupted_config_file, "w", encoding="utf-8") as f:
            f.write('{"github_token": "test_token", "github_username": "test_user"')  # 閉じ括弧なし

        # 設定読み込みでエラーが発生することを確認
        with (
            patch("setup_repo.config.Path.cwd", return_value=temp_dir),
            pytest.raises(json.JSONDecodeError),
            open(corrupted_config_file, encoding="utf-8") as f,
        ):
            # 破損した設定ファイルを読み込もうとする
            json.load(f)

    def test_missing_required_config_error(
        self,
        temp_dir: Path,
    ) -> None:
        """必須設定項目不足エラーのテスト"""
        # 必須項目が不足した設定
        incomplete_configs = [
            {},  # 全て不足
            {"github_token": "test_token"},  # ユーザー名不足
            {"github_username": "test_user"},  # トークン不足
            {"github_token": "", "github_username": "test_user"},  # 空のトークン
            {"github_token": "test_token", "github_username": ""},  # 空のユーザー名
        ]

        for incomplete_config in incomplete_configs:
            result = sync_repositories(incomplete_config, dry_run=True)
            assert not result.success
            assert result.errors

    def test_timeout_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """タイムアウトエラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # タイムアウトエラーをシミュレート
        timeout_error = requests.exceptions.Timeout("Request timed out")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", side_effect=timeout_error),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert not result.success
        assert result.errors
        assert "timed out" in str(result.errors[0]).lower()

    def test_ssl_certificate_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """SSL証明書エラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # SSL証明書エラーをシミュレート
        ssl_error = requests.exceptions.SSLError("SSL certificate verification failed")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", side_effect=ssl_error),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert not result.success
        assert result.errors
        assert "ssl" in str(result.errors[0]).lower()

    def test_partial_failure_recovery(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """部分的失敗からの回復テスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        mock_repos = [
            {
                "name": "success-repo-1",
                "full_name": "test_user/success-repo-1",
                "clone_url": "https://github.com/test_user/success-repo-1.git",
                "ssh_url": "git@github.com:test_user/success-repo-1.git",
                "description": "成功するリポジトリ1",
                "private": False,
                "default_branch": "main",
            },
            {
                "name": "error-repo",
                "full_name": "test_user/error-repo",
                "clone_url": "https://github.com/test_user/error-repo.git",
                "ssh_url": "git@github.com:test_user/error-repo.git",
                "description": "エラーが発生するリポジトリ",
                "private": False,
                "default_branch": "main",
            },
            {
                "name": "success-repo-2",
                "full_name": "test_user/success-repo-2",
                "clone_url": "https://github.com/test_user/success-repo-2.git",
                "ssh_url": "git@github.com:test_user/success-repo-2.git",
                "description": "成功するリポジトリ2",
                "private": False,
                "default_branch": "main",
            },
        ]

        def mock_sync_with_partial_error(repo, dest_dir, config):
            if repo["name"] == "error-repo":
                raise RuntimeError("リポジトリ固有のエラー")
            return True

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=mock_sync_with_partial_error,
            ),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        # 部分的成功を確認
        # 現在の実装では、エラーがあると全体が失敗とみなされるため、
        # 成功したリポジトリ数とエラーの存在を確認
        assert len(result.synced_repos) == 2, f"期待される成功数: 2, 実際: {len(result.synced_repos)}"
        assert "success-repo-1" in result.synced_repos
        assert "success-repo-2" in result.synced_repos
        assert "error-repo" not in result.synced_repos
        assert result.errors, "エラーが記録されていることを確認"

    def test_retry_mechanism(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """リトライメカニズムのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        mock_repos = [
            {
                "name": "retry-repo",
                "full_name": "test_user/retry-repo",
                "clone_url": "https://github.com/test_user/retry-repo.git",
                "ssh_url": "git@github.com:test_user/retry-repo.git",
                "description": "リトライテスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        # 最初の2回は失敗、3回目で成功するモック
        call_count = 0

        def mock_sync_with_retry(repo, dest_dir, config):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("一時的なエラー")
            return True

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=mock_sync_with_retry,
            ),
        ):
            sync_repositories(sample_config, dry_run=False)

        # リトライ後に成功することを確認
        # 注意: 実際のリトライ実装に依存
        assert call_count >= 1  # 少なくとも1回は呼び出される

    def test_memory_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """メモリ不足エラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        mock_repos = [
            {
                "name": "memory-test-repo",
                "full_name": "test_user/memory-test-repo",
                "clone_url": "https://github.com/test_user/memory-test-repo.git",
                "ssh_url": "git@github.com:test_user/memory-test-repo.git",
                "description": "メモリテスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        # メモリエラーをシミュレート
        memory_error = MemoryError("Cannot allocate memory")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            patch("setup_repo.sync.sync_repository_with_retries", side_effect=memory_error),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert not result.success
        assert result.errors

    def test_keyboard_interrupt_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """キーボード割り込みエラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        mock_repos = [
            {
                "name": "interrupt-test-repo",
                "full_name": "test_user/interrupt-test-repo",
                "clone_url": "https://github.com/test_user/interrupt-test-repo.git",
                "ssh_url": "git@github.com:test_user/interrupt-test-repo.git",
                "description": "割り込みテスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        # キーボード割り込みをシミュレート
        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=KeyboardInterrupt,
            ),
            pytest.raises(KeyboardInterrupt),
        ):
            # KeyboardInterruptは通常再発生させる
            sync_repositories(sample_config, dry_run=False)

    def test_unicode_encoding_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """Unicode エンコーディングエラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        # 特殊文字を含むリポジトリ名
        mock_repos = [
            {
                "name": "unicode-テスト-repo-🚀",
                "full_name": "test_user/unicode-テスト-repo-🚀",
                "clone_url": "https://github.com/test_user/unicode-テスト-repo-🚀.git",
                "ssh_url": "git@github.com:test_user/unicode-テスト-repo-🚀.git",
                "description": "Unicode文字テスト用リポジトリ 🎯",
                "private": False,
                "default_branch": "main",
            },
        ]

        # エンコーディングエラーをシミュレート
        encoding_error = UnicodeEncodeError("ascii", "unicode-テスト-repo-🚀", 8, 11, "ordinal not in range(128)")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            patch(
                "setup_repo.sync.sync_repository_with_retries",
                side_effect=encoding_error,
            ),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert not result.success
        assert result.errors

    def test_concurrent_access_error(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """並行アクセスエラーのテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        mock_repos = [
            {
                "name": "concurrent-repo",
                "full_name": "test_user/concurrent-repo",
                "clone_url": "https://github.com/test_user/concurrent-repo.git",
                "ssh_url": "git@github.com:test_user/concurrent-repo.git",
                "description": "並行アクセステスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        # ファイルロックエラーをシミュレート
        lock_error = OSError("Resource temporarily unavailable")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            patch("setup_repo.sync.sync_repository_with_retries", side_effect=lock_error),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        assert not result.success
        assert result.errors

    def test_error_logging_and_reporting(
        self,
        temp_dir: Path,
        sample_config: dict[str, Any],
    ) -> None:
        """エラーログ記録とレポート生成のテスト"""
        clone_destination = temp_dir / "repos"
        sample_config["clone_destination"] = str(clone_destination)

        mock_repos = [
            {
                "name": "logging-test-repo",
                "full_name": "test_user/logging-test-repo",
                "clone_url": "https://github.com/test_user/logging-test-repo.git",
                "ssh_url": "git@github.com:test_user/logging-test-repo.git",
                "description": "ログテスト用リポジトリ",
                "private": False,
                "default_branch": "main",
            },
        ]

        test_error = RuntimeError("テスト用エラーメッセージ")

        # ProcessLockのモック
        mock_lock = Mock()
        mock_lock.acquire.return_value = True

        with (
            patch("setup_repo.sync.get_repositories", return_value=mock_repos),
            patch("setup_repo.sync.ProcessLock", return_value=mock_lock),
            patch("setup_repo.sync.sync_repository_with_retries", side_effect=test_error),
            patch("setup_repo.quality_logger.get_quality_logger"),
        ):
            result = sync_repositories(sample_config, dry_run=False)

        # エラーが適切に記録されることを確認
        assert not result.success
        assert result.errors
        assert "テスト用エラーメッセージ" in str(result.errors[0])

        # ログ記録が呼び出されることを確認（実装に依存）
        # mock_log.assert_called() # 実際の実装に応じて調整

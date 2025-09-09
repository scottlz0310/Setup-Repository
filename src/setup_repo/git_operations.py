#!/usr/bin/env python3
"""Git操作モジュール"""

import shutil
import subprocess
import time
from pathlib import Path


class GitOperations:
    """Git操作を管理するクラス"""

    def __init__(self, config: dict | None = None) -> None:
        """初期化"""
        self.config = config or {}

    def is_git_repository(self, path: Path | str) -> bool:
        """指定されたパスがGitリポジトリかどうかを確認"""
        repo_path = Path(path)
        return (repo_path / ".git").exists()

    def clone_repository(self, repo_url: str, destination: Path | str) -> bool:
        """リポジトリをクローン"""
        dest_path = Path(destination)
        try:
            subprocess.run(
                ["git", "clone", repo_url, str(dest_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def pull_repository(self, repo_path: Path | str) -> bool:
        """既存リポジトリをpull"""
        path = Path(repo_path)
        try:
            subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=path,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False


def choose_clone_url(repo: dict, use_https: bool = False) -> str:
    """SSH/HTTPSを選択してクローンURLを決定"""
    if use_https:
        return repo["clone_url"]

    # SSH鍵の存在チェック
    ssh_keys = [Path.home() / ".ssh" / "id_rsa", Path.home() / ".ssh" / "id_ed25519"]

    if any(key.exists() for key in ssh_keys):
        # SSH接続テスト
        try:
            result = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=3",
                    "git@github.com",
                ],
                capture_output=True,
                timeout=5,
            )
            if result.returncode in [0, 1]:  # 0=成功, 1=認証成功だが接続拒否
                return repo.get("ssh_url", f"git@github.com:{repo['full_name']}.git")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass

    return repo["clone_url"]  # HTTPSにフォールバック


def sync_repository(repo: dict, dest_dir: Path, dry_run: bool = False) -> bool:
    """リポジトリを同期（clone または pull）- 後方互換性のため"""
    config = {"dry_run": dry_run}
    return _sync_repository_once(repo, dest_dir, config)


def sync_repository_with_retries(repo: dict, dest_dir: Path, config: dict) -> bool:
    """リトライ機能付きでリポジトリを同期"""
    repo_name = repo["name"]
    repo_path = dest_dir / repo_name
    max_retries = config.get("max_retries", 2)

    for attempt in range(1, max_retries + 1):
        print(f"   🔁 {repo_name}: 処理中（試行 {attempt}/{max_retries}）")

        if _sync_repository_once(repo, dest_dir, config):
            return True

        if attempt < max_retries:
            print(f"   ⚠️  {repo_name}: 試行 {attempt} 失敗、リトライします")
            if repo_path.exists() and not config.get("dry_run", False):
                shutil.rmtree(repo_path, ignore_errors=True)
            time.sleep(1)

    print(f"   ❌ {repo_name}: 全ての試行が失敗しました")
    return False


def _sync_repository_once(repo: dict, dest_dir: Path, config: dict) -> bool:
    """リポジトリを一度同期"""
    repo_name = repo["name"]
    clone_url = choose_clone_url(repo, config.get("use_https", False))
    repo_path = dest_dir / repo_name
    dry_run = config.get("dry_run", False)

    if repo_path.exists():
        return _update_repository(repo_name, repo_path, config)
    else:
        if config.get("sync_only", False):
            print(f"   ⏭️  {repo_name}: 新規クローンをスキップ（sync_only有効）")
            return True
        return _clone_repository(repo_name, clone_url, repo_path, dry_run)


def _update_repository(repo_name: str, repo_path: Path, config: dict) -> bool:
    """既存リポジトリを更新"""
    print(f"   🔄 {repo_name}: 更新中...")
    dry_run = config.get("dry_run", False)
    auto_stash = config.get("auto_stash", False)

    if dry_run:
        print(f"   ✅ {repo_name}: 更新予定")
        return True

    try:
        stashed = False

        # auto_stashが有効な場合、変更をstash
        if auto_stash:
            stashed = _auto_stash_changes(repo_path)

        # pull実行
        subprocess.run(
            ["git", "pull", "--rebase"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # stashした変更をpop
        if stashed:
            _auto_pop_stash(repo_path)

        print(f"   ✅ {repo_name}: 更新完了")
        return True

    except subprocess.CalledProcessError as e:
        print(f"   ❌ {repo_name}: 更新失敗 - {e.stderr.strip()}")
        if stashed:
            _auto_pop_stash(repo_path)  # エラー時もpopを試行
        return False


def _clone_repository(
    repo_name: str, repo_url: str, repo_path: Path, dry_run: bool
) -> bool:
    """新規リポジトリをクローン"""
    print(f"   📥 {repo_name}: クローン中...")
    if dry_run:
        print(f"   ✅ {repo_name}: クローン予定")
        return True

    try:
        subprocess.run(
            ["git", "clone", repo_url, str(repo_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"   ✅ {repo_name}: クローン完了")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {repo_name}: クローン失敗 - {e.stderr.strip()}")
        return False


def _auto_stash_changes(repo_path: Path) -> bool:
    """変更を自動でstash"""
    try:
        # 変更があるかチェック
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout.strip():
            # 変更をstash
            timestamp = int(time.time())
            subprocess.run(
                ["git", "stash", "push", "-u", "-m", f"autostash-{timestamp}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
    except subprocess.CalledProcessError:
        pass

    return False


def _auto_pop_stash(repo_path: Path) -> bool:
    """stashした変更をpop"""
    try:
        subprocess.run(
            ["git", "stash", "pop"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


# 後方互換性のためのインスタンス作成関数
def create_git_operations(config: dict | None = None) -> GitOperations:
    """GitOperationsインスタンスを作成"""
    return GitOperations(config)

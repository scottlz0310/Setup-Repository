#!/usr/bin/env python3
"""Git操作モジュール"""

import shutil
import subprocess
import time
from pathlib import Path

from .security_helpers import safe_path_join, safe_subprocess


class GitOperations:
    """Git操作を管理するクラス"""

    def __init__(self, config: dict | None = None) -> None:
        """初期化"""
        self.config = config or {}

    def is_git_repository(self, path: Path | str) -> bool:
        """指定されたパスがGitリポジトリかどうかを確認"""
        repo_path = Path(path)
        # パストラバーサル攻撃を防ぐため、安全なパス結合を使用
        try:
            git_path = safe_path_join(repo_path, ".git")
            return git_path.exists()
        except ValueError:
            return False

    def clone_repository(self, repo_url: str, destination: Path | str) -> bool:
        """リポジトリをクローン"""
        dest_path = Path(destination)
        # パストラバーサル攻撃を防ぐため、パスを検証
        try:
            dest_path = dest_path.resolve()
            safe_subprocess(
                ["git", "clone", repo_url, str(dest_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, ValueError):
            return False

    def pull_repository(self, repo_path: Path | str) -> bool:
        """既存リポジトリをpull"""
        path = Path(repo_path)
        try:
            safe_subprocess(
                ["git", "pull", "--rebase"],
                cwd=path,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def is_clean(self) -> bool:
        """作業ディレクトリがクリーンかどうかを確認"""
        try:
            result = safe_subprocess(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            return not result.stdout.strip()
        except subprocess.CalledProcessError:
            return False

    def get_current_branch(self) -> str:
        """現在のブランチ名を取得"""
        try:
            result = safe_subprocess(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def get_current_commit(self) -> str:
        """現在のコミットハッシュを取得"""
        try:
            result = safe_subprocess(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"


def choose_clone_url(repo: dict, use_https: bool = False) -> str:
    """SSH/HTTPSを選択してクローンURLを決定"""
    # データ型の検証とサニタイズ
    clone_url = repo.get("clone_url", "")
    ssh_url = repo.get("ssh_url", "")

    # 不正なデータ型の場合は空文字列に変換
    if not isinstance(clone_url, str):
        clone_url = ""
    if not isinstance(ssh_url, str):
        ssh_url = ""

    if use_https:
        return clone_url

    # SSH鍵の存在チェック
    ssh_keys = [Path.home() / ".ssh" / "id_rsa", Path.home() / ".ssh" / "id_ed25519"]

    if any(key.exists() for key in ssh_keys):
        # SSH鍵が存在する場合はSSHを優先使用
        full_name = repo.get("full_name")
        if full_name and isinstance(full_name, str):
            return ssh_url or f"git@github.com:{full_name}.git"
        else:
            # full_nameが無効な場合はHTTPSにフォールバック
            return clone_url

    return clone_url  # HTTPSにフォールバック


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
        safe_subprocess(
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


def _ensure_github_host_key() -> bool:
    """GitHubのホストキーをknown_hostsに追加

    Returns:
        成功した場合True、失敗または不要な場合False
    """
    ssh_dir = Path.home() / ".ssh"
    known_hosts = ssh_dir / "known_hosts"

    # .sshディレクトリが存在しない場合は作成
    if not ssh_dir.exists():
        ssh_dir.mkdir(mode=0o700, exist_ok=True)

    try:
        # ssh-keyscanでGitHubのホストキーを取得（-tオプションなしで全タイプ取得）
        result = safe_subprocess(
            ["ssh-keyscan", "github.com"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

        if not result.stdout.strip():
            return False

        # 既存のknown_hostsからgithub.comのエントリを削除
        if known_hosts.exists():
            lines = known_hosts.read_text(errors="ignore").splitlines()
            filtered_lines = [line for line in lines if "github.com" not in line.lower()]
            known_hosts.write_text("\n".join(filtered_lines) + "\n" if filtered_lines else "")

        # 新しいホストキーを追加
        with known_hosts.open("a") as f:
            f.write(result.stdout)
            if not result.stdout.endswith("\n"):
                f.write("\n")

        print("   🔑 GitHubのホストキーを更新しました")
        return True

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"   ⚠️  ホストキーの自動追加に失敗: {e}")
        print("   💡 手動で追加: ssh-keyscan github.com >> ~/.ssh/known_hosts")
    return False


# グローバル変数でホストキー追加の実行状況を管理
_host_key_setup_attempted = False


def _clone_repository(repo_name: str, repo_url: str, repo_path: Path, dry_run: bool) -> bool:
    """新規リポジトリをクローン"""
    global _host_key_setup_attempted

    print(f"   📥 {repo_name}: クローン中...")
    if dry_run:
        print(f"   ✅ {repo_name}: クローン予定")
        return True

    # SSH接続の場合、ホストキーを事前に追加（初回のみ）
    if repo_url.startswith("git@github.com") and not _host_key_setup_attempted:
        _host_key_setup_attempted = True
        _ensure_github_host_key()

    try:
        safe_subprocess(
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
        result = safe_subprocess(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout.strip():
            # 変更をstash
            timestamp = int(time.time())
            safe_subprocess(
                ["git", "stash", "push", "-u", "-m", f"autostash-{timestamp}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
    except subprocess.CalledProcessError as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(f"Git stash操作失敗: {e}")

    return False


def _auto_pop_stash(repo_path: Path) -> bool:
    """stashした変更をpop"""
    try:
        safe_subprocess(
            ["git", "stash", "pop"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def commit_and_push_file(
    repo_path: Path,
    file_path: str,
    commit_message: str,
    auto_confirm: bool = False,
    skip_hooks: bool = False,
) -> bool:
    """
    特定のファイルをcommit & pushする

    Args:
        repo_path: リポジトリのパス
        file_path: commitするファイルの相対パス（例: ".gitignore"）
        commit_message: コミットメッセージ
        auto_confirm: Trueの場合は確認なしで実行
        skip_hooks: Trueの場合はpre-commitフックをスキップ（--no-verify）

    Returns:
        成功したらTrue、失敗またはユーザーがキャンセルしたらFalse
    """
    repo_path = Path(repo_path)

    try:
        # 1. リポジトリの状態確認（ファイルに変更があるか）
        result = safe_subprocess(
            ["git", "status", "--porcelain", file_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        if not result.stdout.strip():
            print(f"   ℹ️  {file_path} に変更がありません")
            return True

        # 2. ユーザーに確認（auto_confirmがFalseの場合）
        if not auto_confirm:
            print(f"\n   📤 {file_path} をcommit & pushします")
            print(f"   コミットメッセージ: {commit_message}")
            response = input("   実行しますか？ [Y/n]: ").strip().lower()
            if response == "n":
                print("   ⏭️  pushをキャンセルしました")
                return False

        # 3. git add
        safe_subprocess(
            ["git", "add", file_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # 4. git commit
        commit_cmd = ["git", "commit", "-m", commit_message]
        if skip_hooks:
            commit_cmd.append("--no-verify")

        try:
            safe_subprocess(
                commit_cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            # 5. pre-commitフック失敗時の処理
            if "pre-commit" in e.stderr.lower() or "hook" in e.stderr.lower():
                print("\n   ⚠️  pre-commitフックでエラーが発生しました:")
                print(f"   {e.stderr.strip()}")

                # ファイルが自動修正されたかチェック
                result = safe_subprocess(
                    ["git", "status", "--porcelain", file_path],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )

                if result.stdout.strip():
                    print("\n   🔧 ファイルが自動修正されました。再度commitします...")
                    # 再度add & commit
                    safe_subprocess(
                        ["git", "add", file_path],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    safe_subprocess(
                        commit_cmd,
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                else:
                    # エラーで停止した場合、ユーザーに選択肢を提示
                    print("\n   以下のオプションを選択してください:")
                    print("   1. フックをスキップしてcommit（--no-verify）")
                    print("   2. 手動で修正する（キャンセル）")
                    choice = input("   選択 [1/2]: ").strip()

                    if choice == "1":
                        print("   🔧 フックをスキップしてcommitします...")
                        safe_subprocess(
                            ["git", "commit", "-m", commit_message, "--no-verify"],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                    else:
                        print("   ⏭️  commitをキャンセルしました")
                        # staged状態をリセット
                        safe_subprocess(
                            ["git", "reset", "HEAD", file_path],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        return False
            else:
                # その他のcommitエラー
                print(f"   ❌ commitに失敗しました: {e.stderr.strip()}")
                return False

        # 6. git push
        print(f"   📤 {file_path} をpushしています...")
        try:
            safe_subprocess(
                ["git", "push"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"   ✅ {file_path} をpushしました")
            return True
        except subprocess.CalledProcessError as e:
            # 7. Push失敗時のエラーハンドリング
            error_msg = e.stderr.strip()
            print("\n   ❌ pushに失敗しました:")
            print(f"   {error_msg}")

            if "no upstream" in error_msg.lower() or "set-upstream" in error_msg.lower():
                # upstream設定が必要な場合
                print("\n   🔧 upstreamを設定してpushを再試行します...")
                try:
                    # 現在のブランチ名を取得
                    result = safe_subprocess(
                        ["git", "branch", "--show-current"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    branch = result.stdout.strip()

                    # upstream設定してpush
                    safe_subprocess(
                        ["git", "push", "-u", "origin", branch],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    print(f"   ✅ {file_path} をpushしました")
                    return True
                except subprocess.CalledProcessError as e2:
                    print(f"   ❌ 再試行も失敗しました: {e2.stderr.strip()}")

            print("   ⚠️  手動で `git push` を実行してください")
            return False

    except subprocess.CalledProcessError as e:
        print(f"   ❌ Git操作に失敗しました: {e.stderr.strip()}")
        return False
    except Exception as e:
        print(f"   ❌ エラーが発生しました: {e!s}")
        return False


# 後方互換性のためのインスタンス作成関数
def create_git_operations(config: dict | None = None) -> GitOperations:
    """GitOperationsインスタンスを作成"""
    return GitOperations(config)

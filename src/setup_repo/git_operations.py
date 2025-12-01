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

            # configから設定を取得
            use_shallow = self.config.get("shallow_clone", False)
            clone_depth = self.config.get("clone_depth", 1)
            clone_timeout = self.config.get("clone_timeout", 600)

            # git cloneコマンドを構築
            clone_cmd = ["git", "clone"]
            if use_shallow:
                clone_cmd.extend(["--depth", str(clone_depth)])
            clone_cmd.extend([repo_url, str(dest_path)])

            safe_subprocess(
                clone_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=clone_timeout,
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
        return _clone_repository(repo_name, clone_url, repo_path, dry_run, config)


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
    """GitHubのホストキーをknown_hostsに追加（Windows対応版）

    Returns:
        成功した場合True、失敗または不要な場合False
    """
    import platform

    ssh_dir = Path.home() / ".ssh"
    known_hosts = ssh_dir / "known_hosts"

    # .sshディレクトリが存在しない場合は作成
    if not ssh_dir.exists():
        ssh_dir.mkdir(mode=0o700, exist_ok=True)

    # Windows環境では ssh-keyscan が失敗することが多いため、既知のホストキーを直接追加
    is_windows = platform.system() == "Windows"

    if is_windows:
        print("   🪟 Windows環境を検出 - ホストキーを直接追加します")
        return _add_github_host_key_directly(known_hosts)

    # Linux/macOSでは ssh-keyscan を試行
    try:
        result = safe_subprocess(
            ["ssh-keyscan", "-H", "github.com"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        if not result.stdout.strip():
            print("   ⚠️  ssh-keyscanでのホストキー取得に失敗")
            print("   💡 代替方法でホストキーを追加します...")
            return _add_github_host_key_directly(known_hosts)

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

    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("   ⚠️  ssh-keyscanが利用できません")
        print("   💡 代替方法でホストキーを追加します...")
        return _add_github_host_key_directly(known_hosts)


def _add_github_host_key_directly(known_hosts: Path) -> bool:
    """GitHubの公開ホストキーを直接known_hostsに追加

    Args:
        known_hosts: known_hostsファイルのパス

    Returns:
        成功した場合True
    """
    import platform

    # GitHubの公開ホストキー（2024年時点）
    # https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
    github_host_keys = [
        "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl",
        (
            "github.com ecdsa-sha2-nistp256 "
            "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg="
        ),
        (
            "github.com ssh-rsa "
            "AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk="
        ),
    ]

    try:
        # 既存のknown_hostsからgithub.comのエントリを削除
        if known_hosts.exists():
            lines = known_hosts.read_text(errors="ignore").splitlines()
            filtered_lines = [line for line in lines if "github.com" not in line.lower()]
            content = "\n".join(filtered_lines)
            if content and not content.endswith("\n"):
                content += "\n"
        else:
            content = ""

        # GitHubのホストキーを追加
        with known_hosts.open("w", encoding="utf-8") as f:
            f.write(content)
            for key in github_host_keys:
                f.write(key + "\n")

        # Windowsではファイルパーミッションの設定が異なるため、設定を試みるがエラーは無視
        if platform.system() != "Windows":
            known_hosts.chmod(0o600)

        print("   🔑 GitHubのホストキーを追加しました")
        return True

    except Exception as e:
        print(f"   ❌ ホストキーの追加に失敗: {e}")
        print("   💡 手動で追加してください: ssh-keyscan github.com >> ~/.ssh/known_hosts")
        return False


# グローバル変数でホストキー追加の実行状況を管理
_host_key_setup_attempted = False


def _verify_ssh_connection() -> tuple[bool, str]:
    """SSH接続を検証

    Returns:
        (成功したかどうか, エラーメッセージ)
    """
    try:
        result = safe_subprocess(
            ["ssh", "-T", "git@github.com"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

        # GitHub SSHは常にexit code 1を返すが、成功メッセージが含まれる
        if "successfully authenticated" in result.stderr.lower():
            return True, ""

        # エラーメッセージを返す
        return False, result.stderr.strip()

    except subprocess.TimeoutExpired:
        return False, "SSH接続がタイムアウトしました"
    except Exception as e:
        return False, str(e)


def _clone_repository(
    repo_name: str, repo_url: str, repo_path: Path, dry_run: bool, config: dict | None = None
) -> bool:
    """新規リポジトリをクローン"""
    global _host_key_setup_attempted

    config = config or {}

    # 大きなリポジトリかどうかを判定
    large_repos = config.get("large_repos", [])
    is_large_repo = repo_name in large_repos

    # shallow cloneの設定を取得
    use_shallow = config.get("shallow_clone", False) or is_large_repo
    clone_depth = config.get("clone_depth", 1)

    # タイムアウトの設定を取得
    clone_timeout = config.get("clone_timeout", 600)  # デフォルト: 10分

    if use_shallow:
        print(f"   📥 {repo_name}: クローン中（shallow clone, depth={clone_depth}）...")
    else:
        print(f"   📥 {repo_name}: クローン中...")

    if dry_run:
        print(f"   ✅ {repo_name}: クローン予定")
        return True

    # SSH接続の場合、ホストキーを事前に追加（初回のみ）
    if repo_url.startswith("git@github.com") and not _host_key_setup_attempted:
        _host_key_setup_attempted = True

        # ホストキーを追加
        host_key_added = _ensure_github_host_key()
        if not host_key_added:
            print("   ⚠️  ホストキー追加に失敗しましたが、クローンを試行します")

        # SSH接続を検証
        print("   🔍 SSH接続を検証中...")
        ssh_ok, ssh_error = _verify_ssh_connection()

        if not ssh_ok:
            print(f"   ❌ SSH接続検証失敗: {ssh_error}")
            print("\n   💡 SSH接続のトラブルシューティング:")
            print("      1. SSH agentが起動しているか確認: ssh-add -l")
            print("      2. SSH鍵を追加: ssh-add ~/.ssh/id_ed25519")
            print("      3. SSH接続をテスト: ssh -T git@github.com")
            print("      4. known_hostsを確認: cat ~/.ssh/known_hosts | grep github")
            return False

        print("   ✅ SSH接続検証成功")

    try:
        # git cloneコマンドを構築
        clone_cmd = ["git", "clone"]
        if use_shallow:
            clone_cmd.extend(["--depth", str(clone_depth)])
        clone_cmd.extend([repo_url, str(repo_path)])

        safe_subprocess(
            clone_cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=clone_timeout,
        )

        if use_shallow:
            print(f"   ✅ {repo_name}: クローン完了（shallow clone）")
        else:
            print(f"   ✅ {repo_name}: クローン完了")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip()
        print(f"   ❌ {repo_name}: クローン失敗 - {error_msg}")
        return False
    except subprocess.TimeoutExpired:
        print(f"   ❌ {repo_name}: クローンがタイムアウトしました（{clone_timeout}秒）")
        print("   💡 config.jsonで 'clone_timeout' を増やすか、")
        print(f"      'large_repos' リストに '{repo_name}' を追加してください")
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

"""リポジトリ同期機能"""

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .git_operations import choose_clone_url, sync_repository_with_retries
from .github_api import get_repositories
from .gitignore_manager import GitignoreManager
from .platform_detector import PlatformDetector
from .python_env import setup_python_environment
from .safety_check import (
    check_unpushed_changes,
    create_emergency_backup,
    prompt_user_action,
)
from .utils import ProcessLock, TeeLogger
from .uv_installer import ensure_uv
from .vscode_setup import apply_vscode_template


@dataclass
class SyncResult:
    """同期結果を管理するデータクラス"""

    success: bool
    synced_repos: list[str]
    errors: list[Exception]
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


def sync_repositories(config: dict, dry_run: bool = False) -> SyncResult:
    """リポジトリ同期のメイン処理"""
    synced_repos = []
    errors: list[Exception] = []
    owner = config.get("owner") or config.get("github_username")
    dest = config.get("dest") or config.get("clone_destination")
    dry_run = dry_run or config.get("dry_run", False)
    force = config.get("force", False)

    platform_detector = PlatformDetector()
    platform = platform_detector.detect_platform()

    # 検出した設定を表示
    print("\\n[INFO] 設定情報:")
    print(f"   プラットフォーム: {platform}")
    print(f"   オーナー: {owner or '[ERROR] 検出されませんでした'}")
    print(f"   保存先: {dest}")
    token_status = "[OK] 検出されました" if config.get("github_token") else "[ERROR] 見つかりません"
    print(f"   GitHubトークン: {token_status}")

    if not owner:
        error_msg = "GitHubオーナーが検出されませんでした"
        print(f"\\n[ERROR] {error_msg}")
        print("   [FIX] GITHUB_USER 環境変数")
        print("   [FIX] git config --global user.name")
        print("   [FIX] config.local.json に 'owner' フィールドを作成")
        errors.append(ValueError(error_msg))
        return SyncResult(success=False, synced_repos=[], errors=errors)

    # ロック取得
    if not dry_run:
        import os
        import tempfile

        # テスト環境では一意なロックファイルを使用
        if os.environ.get("PYTEST_CURRENT_TEST"):
            lock = ProcessLock.create_test_lock("sync")
        else:
            default_lock_file = str(Path(tempfile.gettempdir()) / "repo-sync.lock")
            lock_file = config.get("lock_file", default_lock_file)
            lock = ProcessLock(lock_file)

        if not lock.acquire():
            print(f"[ERROR] 別のプロセスが実行中です（ロック: {lock.lock_file}）")
            sys.exit(1)

    # ログセットアップ
    logger = TeeLogger(config.get("log_file") if not dry_run else None)

    print("\\n[START] セットアップを開始します...")

    # uvインストールチェック
    if not config.get("skip_uv_install", False):
        ensure_uv()

    # リポジトリ一覧取得
    print("\\n[INFO] リポジトリ一覧を取得中...")
    try:
        repos = get_repositories(owner, config.get("github_token"))
    except Exception as e:
        print(f"[ERROR] リポジトリ取得エラー: {e}")
        errors.append(e)
        return SyncResult(success=False, synced_repos=[], errors=errors)

    if not repos:
        error_msg = "リポジトリが見つかりませんでした"
        print(f"[ERROR] {error_msg}")
        errors.append(ValueError(error_msg))
        return SyncResult(success=False, synced_repos=[], errors=errors)

    print(f"[INFO] {len(repos)}個のリポジトリを発見")

    # 実際の接続方式を表示
    sample_url = choose_clone_url(repos[0], config.get("use_https", False))
    # sample_urlが文字列でない場合の安全な処理
    if isinstance(sample_url, str) and sample_url:
        connection_type = "SSH" if sample_url.startswith("git@") else "HTTPS"
    else:
        connection_type = "UNKNOWN"
    print(f"[INFO] 実際の接続方式: {connection_type}")

    # 保存先ディレクトリ作成
    dest_dir = Path(dest)
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    # リポジトリ同期
    print("\\n[SYNC] リポジトリ同期中...")
    success_count = 0

    for repo in repos:
        # リポジトリデータの基本検証
        repo_name = repo.get("name")
        if not isinstance(repo_name, str) or not repo_name:
            # 不正なリポジトリ名の場合はスキップ
            print(f"   [WARN] 不正なリポジトリ名をスキップ: {repo_name}")
            errors.append(ValueError(f"不正なリポジトリ名: {repo_name}"))
            continue

        # 必須フィールドの検証
        if not repo.get("clone_url") and not repo.get("ssh_url"):
            print(f"   [WARN] {repo_name}: クローンURLが見つかりません")
            errors.append(ValueError(f"{repo_name}: クローンURLが見つかりません"))
            continue
        repo_path = dest_dir / repo_name

        # 安全性チェック
        if repo_path.exists() and not dry_run and not force:
            has_issues, issues = check_unpushed_changes(repo_path)
            if has_issues:
                choice = prompt_user_action(repo_name, issues)
                if choice == "q":
                    print("\\n[STOP] ユーザーによって中断されました")
                    sys.exit(0)
                elif choice == "s":
                    print(f"   [SKIP] {repo_name}: スキップしました")
                    continue
                elif choice == "c":
                    create_emergency_backup(repo_path)

        # Git同期
        try:
            if dry_run:
                # ドライランモードでは実際の同期は行わない
                print(f"   [DRY] {repo_name}: ドライランモード - 同期をスキップ")
                synced_repos.append(repo_name)
                success_count += 1
            elif sync_repository_with_retries(repo, dest_dir, config):
                success_count += 1
                synced_repos.append(repo_name)

                # .gitignore管理
                gitignore_manager = GitignoreManager(repo_path)
                gitignore_manager.setup_gitignore(dry_run)

                # VS Code設定適用
                apply_vscode_template(repo_path, platform, dry_run)

                # Python環境セットアップ
                setup_python_environment(repo_path, dry_run)
        except Exception as e:
            print(f"   [ERROR] {repo_name}: 同期エラー - {e}")
            errors.append(e)

    print(f"\\n[DONE] 完了: {success_count}/{len(repos)} リポジトリを同期しました")
    logger.close()

    # 結果を返す
    return SyncResult(success=len(errors) == 0, synced_repos=synced_repos, errors=errors)

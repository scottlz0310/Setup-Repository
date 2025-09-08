"""リポジトリ同期機能"""
import sys
from pathlib import Path
from typing import Dict

from .github_api import get_repositories
from .git_operations import sync_repository_with_retries, choose_clone_url
from .safety_check import check_unpushed_changes, prompt_user_action, create_emergency_backup
from .python_env import setup_python_environment
from .vscode_setup import apply_vscode_template
from .utils import ProcessLock, TeeLogger, detect_platform
from .uv_installer import ensure_uv
from .gitignore_manager import GitignoreManager


def sync_repositories(config: Dict) -> None:
    """リポジトリ同期のメイン処理"""
    owner = config.get("owner")
    dest = config.get("dest")
    dry_run = config.get("dry_run", False)
    force = config.get("force", False)
    
    platform = detect_platform()
    
    # 🔍 検出した設定を表示
    print("\\n🔍 設定情報:")
    print(f"   📱 プラットフォーム: {platform}")
    print(f"   👤 オーナー: {owner or '❌ 検出されませんでした'}")
    print(f"   📁 保存先: {dest}")
    print(f"   🔑 GitHubトークン: {'✅ 検出されました' if config.get('github_token') else '❌ 見つかりません'}")
    
    if not owner:
        print("\\n❌ GitHubオーナーが検出されませんでした。以下のいずれかを設定してください:")
        print("   🔧 GITHUB_USER 環境変数")
        print("   🔧 git config --global user.name")
        print("   🔧 config.local.json に 'owner' フィールドを作成")
        sys.exit(1)
    
    # ロック取得
    if not dry_run:
        lock_file = config.get('lock_file', '/tmp/repo-sync.lock')
        lock = ProcessLock(lock_file)
        if not lock.acquire():
            print(f"❌ 別のプロセスが実行中です（ロック: {lock_file}）")
            sys.exit(1)
    
    # ログセットアップ
    logger = TeeLogger(config.get('log_file') if not dry_run else None)
    
    print("\\n🚀 セットアップを開始します...")
    
    # uvインストールチェック
    if not config.get('skip_uv_install', False):
        ensure_uv()
    
    # リポジトリ一覧取得
    print("\\n📡 リポジトリ一覧を取得中...")
    repos = get_repositories(owner, config.get('github_token'))
    
    if not repos:
        print("❌ リポジトリが見つかりませんでした")
        sys.exit(1)
    
    print(f"📋 {len(repos)}個のリポジトリを発見")
    
    # 実際の接続方式を表示
    sample_url = choose_clone_url(repos[0], config.get('use_https', False))
    connection_type = "SSH" if sample_url.startswith("git@") else "HTTPS"
    print(f"🔗 実際の接続方式: {connection_type}")
    
    # 保存先ディレクトリ作成
    dest_dir = Path(dest)
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
    
    # リポジトリ同期
    print("\\n🔄 リポジトリ同期中...")
    success_count = 0
    
    for repo in repos:
        repo_name = repo['name']
        repo_path = dest_dir / repo_name
        
        # 安全性チェック
        if repo_path.exists() and not dry_run and not force:
            has_issues, issues = check_unpushed_changes(repo_path)
            if has_issues:
                choice = prompt_user_action(repo_name, issues)
                if choice == 'q':
                    print("\\n🛑 ユーザーによって中断されました")
                    sys.exit(0)
                elif choice == 's':
                    print(f"   ⏭️  {repo_name}: スキップしました")
                    continue
                elif choice == 'c':
                    create_emergency_backup(repo_path)
        
        # Git同期
        if sync_repository_with_retries(repo, dest_dir, config):
            success_count += 1
            
            # .gitignore管理
            gitignore_manager = GitignoreManager(repo_path)
            gitignore_manager.setup_gitignore(dry_run)
            
            # VS Code設定適用
            apply_vscode_template(repo_path, platform, dry_run)
            
            # Python環境セットアップ
            setup_python_environment(repo_path, dry_run)
    
    print(f"\\n✅ 完了: {success_count}/{len(repos)} リポジトリを同期しました")
    logger.close()
#!/usr/bin/env python3
"""
クロスプラットフォームGitHubリポジトリセットアップツール
Windows, Linux, macOSで統一された設定をサポート
"""
import os
import sys
import json
import subprocess
import argparse
import platform
from pathlib import Path
from typing import Dict, Optional

from github_api import get_repositories
from git_operations import sync_repository_with_retries, choose_clone_url
from safety_check import check_unpushed_changes, prompt_user_action, create_emergency_backup
from python_env import setup_python_environment
from vscode_setup import apply_vscode_template
from utils import ProcessLock, TeeLogger, detect_platform
from uv_installer import ensure_uv

def get_github_token() -> Optional[str]:
    """環境変数またはgh CLIからGitHubトークンを自動検出"""
    # 環境変数を最初に試す
    token = os.getenv('GITHUB_TOKEN')
    if token:
        return token
    
    # gh CLIをフォールバックとして試す
    try:
        result = subprocess.run(['gh', 'auth', 'token'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def auto_detect_config() -> Dict:
    """環境から設定を自動検出"""
    config = {
        "owner": os.getenv('GITHUB_USER', ''),
        "dest": str(Path.home() / "workspace"),
        "github_token": get_github_token(),
        "use_https": False,
        "max_retries": 2,
        "skip_uv_install": False,
        "auto_stash": False,
        "sync_only": False,
        "log_file": str(Path.home() / "logs" / "repo-sync.log")
    }
    
    # Try to get username from git config
    if not config["owner"]:
        try:
            result = subprocess.run(['git', 'config', '--global', 'user.name'], 
                                  capture_output=True, text=True, check=True)
            config["owner"] = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    
    return config

def load_config() -> Dict:
    """自動検出フォールバック付きで設定を読み込み"""
    # 自動検出した設定から開始
    config = auto_detect_config()
    
    # ファイル設定が存在する場合は上書き
    config_files = ['config.local.json', 'config.json']
    for config_file in config_files:
        config_path = Path(__file__).parent / config_file
        if config_path.exists():
            with open(config_path) as f:
                file_config = json.load(f)
                config.update(file_config)
            break
    
    return config

def detect_platform() -> str:
    """現在のプラットフォームを検出"""
    system = platform.system().lower()
    if system == "windows" or os.name == "nt":
        return "windows"
    elif "microsoft" in platform.release().lower():
        return "wsl"
    return "linux"

def main():
    config = load_config()
    
    parser = argparse.ArgumentParser(description="🚀 GitHubリポジトリセットアップツール")
    parser.add_argument("--owner", default=config.get("owner", ""), help="GitHubオーナー名")
    parser.add_argument("--dest", default=config.get("dest"), help="クローン先ディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="実行内容を表示のみ（実際の処理は行わない）")
    parser.add_argument("--force", action="store_true", help="安全性チェックをスキップ")
    parser.add_argument("--use-https", action="store_true", help="SSHではなくHTTPSでクローン")
    parser.add_argument("--sync-only", action="store_true", help="新規クローンを行わず、既存リポジトリのみ更新")
    parser.add_argument("--auto-stash", action="store_true", help="ローカル変更を自動でstash")
    parser.add_argument("--skip-uv-install", action="store_true", help="uvの自動インストールをスキップ")
    
    args = parser.parse_args()
    
    # 設定をコマンドライン引数で上書き
    config.update({
        'dry_run': args.dry_run,
        'use_https': args.use_https or config.get('use_https', False),
        'sync_only': args.sync_only or config.get('sync_only', False),
        'auto_stash': args.auto_stash or config.get('auto_stash', False),
        'skip_uv_install': args.skip_uv_install or config.get('skip_uv_install', False)
    })
    
    platform = detect_platform()
    
    # 🔍 検出した設定を表示
    print("\n🔍 設定情報:")
    print(f"   📱 プラットフォーム: {platform}")
    print(f"   👤 オーナー: {args.owner or '❌ 検出されませんでした'}")
    print(f"   📁 保存先: {args.dest}")
    print(f"   🔑 GitHubトークン: {'✅ 検出されました' if config.get('github_token') else '❌ 見つかりません'}")
    
    if not args.owner:
        print("\n❌ GitHubオーナーが検出されませんでした。以下のいずれかを設定してください:")
        print("   🔧 GITHUB_USER 環境変数")
        print("   🔧 git config --global user.name")
        print("   🔧 config.local.json に 'owner' フィールドを作成")
        sys.exit(1)
    
    # ロック取得
    if not args.dry_run:
        lock_file = config.get('lock_file', '/tmp/repo-sync.lock')
        lock = ProcessLock(lock_file)
        if not lock.acquire():
            print(f"❌ 別のプロセスが実行中です（ロック: {lock_file}）")
            sys.exit(1)
    
    # ログセットアップ
    logger = TeeLogger(config.get('log_file') if not args.dry_run else None)
    
    print("\n🚀 セットアップを開始します...")
    
    # uvインストールチェック
    if not config.get('skip_uv_install', False):
        ensure_uv()
    
    # リポジトリ一覧取得
    print("\n📡 リポジトリ一覧を取得中...")
    repos = get_repositories(args.owner, config.get('github_token'))
    
    if not repos:
        print("❌ リポジトリが見つかりませんでした")
        sys.exit(1)
    
    print(f"📋 {len(repos)}個のリポジトリを発見")
    
    # 実際の接続方式を表示
    sample_url = choose_clone_url(repos[0], config.get('use_https', False))
    connection_type = "SSH" if sample_url.startswith("git@") else "HTTPS"
    print(f"🔗 実際の接続方式: {connection_type}")
    
    # 保存先ディレクトリ作成
    dest_dir = Path(args.dest)
    if not args.dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
    
    # リポジトリ同期
    print("\n🔄 リポジトリ同期中...")
    success_count = 0
    
    for repo in repos:
        repo_name = repo['name']
        repo_path = dest_dir / repo_name
        
        # 安全性チェック
        if repo_path.exists() and not args.dry_run and not args.force:
            has_issues, issues = check_unpushed_changes(repo_path)
            if has_issues:
                choice = prompt_user_action(repo_name, issues)
                if choice == 'q':
                    print("\n🛑 ユーザーによって中断されました")
                    sys.exit(0)
                elif choice == 's':
                    print(f"   ⏭️  {repo_name}: スキップしました")
                    continue
                elif choice == 'c':
                    create_emergency_backup(repo_path)
        
        # Git同期
        if sync_repository_with_retries(repo, dest_dir, config):
            success_count += 1
            
            # VS Code設定適用
            apply_vscode_template(repo_path, platform, args.dry_run)
            
            # Python環境セットアップ
            setup_python_environment(repo_path, args.dry_run)
    
    print(f"\n✅ 完了: {success_count}/{len(repos)} リポジトリを同期しました")
    logger.close()

if __name__ == "__main__":
    main()
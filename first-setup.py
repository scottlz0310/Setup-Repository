#!/usr/bin/env python3
"""Initial setup script to create personal configuration"""
import json
import os
import subprocess
from pathlib import Path

def get_github_token():
    """GitHubトークンの自動検出"""
    token = os.getenv('GITHUB_TOKEN')
    if token:
        return token
    
    try:
        result = subprocess.run(['gh', 'auth', 'token'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_github_user():
    """GitHubユーザー名の自動検出"""
    user = os.getenv('GITHUB_USER')
    if user:
        return user
    
    try:
        result = subprocess.run(['git', 'config', '--global', 'user.name'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def install_uv():
    """モダンパッケージマネージャーでuvをインストールし、フォールバックでpipを使用"""
    system = os.name
    
    if system == 'nt':  # Windows
        # scoopを試す
        try:
            subprocess.run(['scoop', 'install', 'uv'], check=True)
            print("✅ scoopでuvをインストールしました")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # wingetを試す
        try:
            subprocess.run(['winget', 'install', '--id=astral-sh.uv'], check=True)
            print("✅ wingetでuvをインストールしました")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    
    else:  # Linux/macOS
        # snapを試す
        try:
            subprocess.run(['sudo', 'snap', 'install', '--classic', 'uv'], check=True)
            print("✅ snapでuvをインストールしました")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # 公式インストーラーを試す
        try:
            subprocess.run(['curl', '-LsSf', 'https://astral.sh/uv/install.sh'], 
                         stdout=subprocess.PIPE, check=True)
            result = subprocess.run(['sh'], input=subprocess.PIPE, check=True)
            print("✅ 公式インストーラーでuvをインストールしました")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    
    # フォールバック: pip
    try:
        subprocess.run(['pip', 'install', 'uv'], check=True)
        print("✅ pipでuvをインストールしました")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return False

def check_dependencies():
    """必要なツールのチェックとインストール案内"""
    missing = []
    
    # Python チェック
    try:
        import sys
        if sys.version_info < (3, 9):
            missing.append(f"Python 3.9+ (現在: {sys.version_info[0]}.{sys.version_info[1]})")
    except:
        missing.append("Python 3.9+")
    
    # git チェック
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append("git")
    
    # uv チェック（推奨）
    uv_found = True
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, check=True, text=True)
        uv_version = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        uv_found = False
        uv_version = None
    
    # GitHub CLI チェック（推奨）
    gh_found = True
    try:
        subprocess.run(['gh', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        gh_found = False
    
    if missing:
        print("❌ 必須ツールが不足しています:")
        for tool in missing:
            print(f"   - {tool}")
        print("\n続行する前に不足しているツールをインストールしてください。")
        return False
    
    if uv_found:
        print(f"✅ uv がインストール済みです: {uv_version}")
    else:
        print("⚠️  uv が見つかりません。Python環境管理を改善するためにインストールを推奨します:")
        
        # プラットフォーム別のモダンパッケージマネージャーを推奨
        system = os.name
        if system == 'nt':  # Windows
            print("   推奨: scoop install uv")
            print("   または: winget install --id=astral-sh.uv")
        else:  # Linux/macOS
            # snapの利用可能性をチェック
            snap_available = False
            try:
                subprocess.run(['snap', '--version'], capture_output=True, check=True)
                snap_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            if snap_available:
                print("   推奨: sudo snap install --classic uv")
            else:
                print("   推奨: curl -LsSf https://astral.sh/uv/install.sh | sh")
        
        print("   フォールバック: pip install uv")
        
        # ユーザーにインストールを試みるか確認
        response = input("\nuvを自動インストールしますか? (y/N): ").strip().lower()
        if response in ['y', 'yes', 'はい']:
            if not install_uv():
                print("❌ uvのインストールに失敗しました。手動でインストールしてから再実行してください。")
                return False
        else:
            print("❌ uvのインストールがスキップされました。手動でインストールしてから再実行してください。")
            return False
    
    if not gh_found:
        print("⚠️  GitHub CLI が見つかりません。認証を簡素化するためにインストールを推奨します:")
        print("   https://cli.github.com/")
    
    return True

def setup():
    """自動検出した値で個人設定を作成"""
    print("🔧 依存関係をチェック中...")
    if not check_dependencies():
        return
    
    config_path = Path("config.local.json")
    
    if config_path.exists():
        print(f"✅ {config_path} は既に存在します")
        return
    
    # Auto-detect configuration
    config = {
        "owner": get_github_user() or "YOUR_GITHUB_USERNAME",
        "dest": str(Path.home() / "workspace"),
        "github_token": get_github_token() or "YOUR_GITHUB_TOKEN",
        "use_https": False,
        "max_retries": 2,
        "skip_uv_install": False,
        "auto_stash": False,
        "sync_only": False,
        "log_file": str(Path.home() / "logs" / "repo-sync.log")
    }
    
    # Write config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ 自動検出した値で {config_path} を作成しました:")
    print(f"   オーナー: {config['owner']}")
    print(f"   トークン: {'検出されました' if config['github_token'] != 'YOUR_GITHUB_TOKEN' else '見つかりません'}")
    print(f"   保存先: {config['dest']}")
    
    if config['owner'] == "YOUR_GITHUB_USERNAME" or config['github_token'] == "YOUR_GITHUB_TOKEN":
        print(f"📝 プレースホルダー値を更新するために {config_path} を編集してください")
    
    print("\n✅ セットアップ完了! 次の手順:")
    print("   1. 必要に応じて config.local.json を確認/編集")
    print("   2. 実行: python repo-sync.py --dry-run")
    print("   3. 実行: python repo-sync.py")

if __name__ == "__main__":
    setup()
"""インタラクティブセットアップ機能"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .platform_detector import detect_platform, get_available_package_managers, get_install_commands
from .config import get_github_token, get_github_user


class SetupWizard:
    """セットアップウィザード"""
    
    def __init__(self):
        self.platform_info = detect_platform()
        self.config = {}
        self.errors = []
        
    def welcome_message(self):
        """ウェルカムメッセージ"""
        print("🚀 セットアップリポジトリへようこそ!")
        print("=" * 50)
        print(f"📱 検出されたプラットフォーム: {self.platform_info.display_name}")
        print("\\nこのツールは以下の機能を提供します:")
        print("  • GitHubリポジトリの自動クローン・同期")
        print("  • クロスプラットフォーム対応の開発環境セットアップ")
        print("  • VS Code設定の自動適用")
        print("  • Python仮想環境の自動管理")
        print("\\n数分で完了します。始めましょう! 🎯")
        print("=" * 50)
    
    def check_prerequisites(self) -> bool:
        """前提条件のチェック"""
        print("\\n🔍 前提条件をチェック中...")
        
        # Python バージョンチェック
        python_version = sys.version_info
        if python_version < (3, 9):
            self.errors.append(f"Python 3.9以上が必要です (現在: {python_version[0]}.{python_version[1]})")
        else:
            print(f"✅ Python {python_version[0]}.{python_version[1]}.{python_version[2]}")
        
        # Git チェック
        try:
            result = subprocess.run(['git', '--version'], 
                                  capture_output=True, text=True, check=True)
            print(f"✅ {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.errors.append("Git がインストールされていません")
        
        if self.errors:
            print("\\n❌ 前提条件が満たされていません:")
            for error in self.errors:
                print(f"   • {error}")
            self._show_prerequisite_help()
            return False
        
        return True
    
    def _show_prerequisite_help(self):
        """前提条件のインストールヘルプ"""
        print("\\n📋 インストール方法:")
        
        if self.platform_info.name == "windows":
            print("\\n🪟 Windows:")
            print("  Python: https://www.python.org/downloads/")
            print("  Git: https://git-scm.com/download/win")
            print("  または: winget install Python.Python Git.Git")
        
        elif self.platform_info.name == "wsl":
            print("\\n🐧 WSL:")
            print("  sudo apt update")
            print("  sudo apt install python3 python3-pip git")
        
        elif self.platform_info.name == "macos":
            print("\\n🍎 macOS:")
            print("  brew install python git")
            print("  または: https://www.python.org/downloads/")
        
        else:  # Linux
            print("\\n🐧 Linux:")
            print("  sudo apt update")
            print("  sudo apt install python3 python3-pip git")
    
    def setup_package_managers(self) -> bool:
        """パッケージマネージャーのセットアップ"""
        print("\\n📦 パッケージマネージャーをチェック中...")
        
        available_managers = get_available_package_managers(self.platform_info)
        
        if not available_managers:
            print("⚠️  推奨パッケージマネージャーが見つかりません")
            self._show_package_manager_help()
            
            response = input("\\n手動でインストールしましたか? 続行しますか? (y/N): ").strip().lower()
            return response in ['y', 'yes', 'はい']
        
        print("✅ 利用可能なパッケージマネージャー:")
        for manager in available_managers:
            print(f"   • {manager}")
        
        return True
    
    def _show_package_manager_help(self):
        """パッケージマネージャーのインストールヘルプ"""
        print("\\n📋 推奨パッケージマネージャーのインストール:")
        
        if self.platform_info.name == "windows":
            print("\\n🪟 Windows - Scoop (推奨):")
            print("  PowerShellで実行:")
            print("  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser")
            print("  Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression")
            print("\\n  または Winget (Windows 10/11標準):")
            print("  既にインストール済みの場合があります")
        
        elif self.platform_info.name in ["wsl", "linux"]:
            print("\\n🐧 Linux/WSL - Snap:")
            print("  sudo apt update && sudo apt install snapd")
        
        elif self.platform_info.name == "macos":
            print("\\n🍎 macOS - Homebrew:")
            print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
    
    def install_tools(self) -> bool:
        """必要ツールのインストール"""
        print("\\n🔧 必要ツールをインストール中...")
        
        # uv チェック
        uv_installed = self._check_tool("uv")
        if not uv_installed:
            if not self._install_uv():
                return False
        
        # GitHub CLI チェック（オプション）
        gh_installed = self._check_tool("gh")
        if not gh_installed:
            print("⚠️  GitHub CLI が見つかりません（オプション）")
            response = input("GitHub CLI をインストールしますか? 認証が簡単になります (Y/n): ").strip().lower()
            if response not in ['n', 'no', 'いいえ']:
                self._install_gh()
        
        return True
    
    def _check_tool(self, tool: str) -> bool:
        """ツールの存在チェック"""
        try:
            result = subprocess.run([tool, '--version'], 
                                  capture_output=True, text=True, check=True)
            print(f"✅ {tool}: {result.stdout.strip().split()[0]} {result.stdout.strip().split()[1] if len(result.stdout.strip().split()) > 1 else ''}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _install_uv(self) -> bool:
        """uvのインストール"""
        print("\\n📦 uv をインストール中...")
        
        available_managers = get_available_package_managers(self.platform_info)
        install_commands = get_install_commands(self.platform_info)
        
        # 推奨順でインストールを試行
        for manager in available_managers:
            if manager in install_commands:
                try:
                    cmd = install_commands[manager][0]  # uv install command
                    print(f"   {manager} を使用: {cmd}")
                    
                    if manager == "curl":
                        # curl の場合は特別処理
                        subprocess.run(cmd, shell=True, check=True)
                    else:
                        subprocess.run(cmd.split(), check=True)
                    
                    print("✅ uv のインストールが完了しました")
                    return True
                    
                except subprocess.CalledProcessError:
                    print(f"❌ {manager} でのインストールに失敗")
                    continue
        
        # フォールバック: pip
        try:
            subprocess.run(['pip', 'install', 'uv'], check=True)
            print("✅ pip で uv をインストールしました")
            return True
        except subprocess.CalledProcessError:
            print("❌ すべてのインストール方法が失敗しました")
            return False
    
    def _install_gh(self) -> bool:
        """GitHub CLI のインストール"""
        available_managers = get_available_package_managers(self.platform_info)
        install_commands = get_install_commands(self.platform_info)
        
        for manager in available_managers:
            if manager in install_commands and len(install_commands[manager]) > 1:
                try:
                    cmd = install_commands[manager][1]  # gh install command
                    print(f"   {manager} を使用: {cmd}")
                    subprocess.run(cmd.split(), check=True)
                    print("✅ GitHub CLI のインストールが完了しました")
                    return True
                except subprocess.CalledProcessError:
                    continue
        
        print("⚠️  GitHub CLI の自動インストールに失敗しました")
        print("   手動インストール: https://cli.github.com/")
        return False
    
    def configure_github(self):
        """GitHub設定の構成"""
        print("\\n🔑 GitHub設定を構成中...")
        
        # ユーザー名の検出・設定
        username = get_github_user()
        if not username:
            print("\\n👤 GitHubユーザー名が検出されませんでした")
            username = input("GitHubユーザー名を入力してください: ").strip()
            
            if username:
                # git config に設定
                try:
                    subprocess.run(['git', 'config', '--global', 'user.name', username], check=True)
                    print(f"✅ Git設定にユーザー名を保存しました: {username}")
                except subprocess.CalledProcessError:
                    print("⚠️  Git設定の保存に失敗しました")
        else:
            print(f"✅ GitHubユーザー名: {username}")
        
        self.config['owner'] = username
        
        # トークンの検出・設定
        token = get_github_token()
        if not token:
            print("\\n🔐 GitHubトークンが検出されませんでした")
            print("\\n以下の方法でトークンを設定できます:")
            print("  1. GitHub CLI: gh auth login")
            print("  2. 環境変数: export GITHUB_TOKEN=your_token")
            print("  3. 手動設定: config.local.json で後から設定")
            
            choice = input("\\n今すぐ GitHub CLI で認証しますか? (Y/n): ").strip().lower()
            if choice not in ['n', 'no', 'いいえ']:
                try:
                    subprocess.run(['gh', 'auth', 'login'], check=True)
                    token = get_github_token()
                    if token:
                        print("✅ GitHub認証が完了しました")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("⚠️  GitHub CLI認証に失敗しました")
        else:
            print("✅ GitHubトークンが検出されました")
        
        self.config['github_token'] = token or "YOUR_GITHUB_TOKEN"
    
    def configure_workspace(self):
        """ワークスペース設定"""
        print("\\n📁 ワークスペース設定...")
        
        default_workspace = str(Path.home() / "workspace")
        print(f"\\nデフォルトのワークスペース: {default_workspace}")
        
        custom_path = input("別のパスを使用しますか? (空白でデフォルト): ").strip()
        workspace_path = custom_path if custom_path else default_workspace
        
        # ディレクトリの作成確認
        workspace_dir = Path(workspace_path)
        if not workspace_dir.exists():
            try:
                workspace_dir.mkdir(parents=True, exist_ok=True)
                print(f"✅ ワークスペースディレクトリを作成しました: {workspace_path}")
            except OSError as e:
                print(f"❌ ディレクトリ作成に失敗: {e}")
                workspace_path = default_workspace
        
        self.config['dest'] = workspace_path
    
    def save_config(self):
        """設定ファイルの保存"""
        print("\\n💾 設定を保存中...")
        
        # 完全な設定を構築
        full_config = {
            "owner": self.config.get('owner', 'YOUR_GITHUB_USERNAME'),
            "dest": self.config.get('dest', str(Path.home() / "workspace")),
            "github_token": self.config.get('github_token', 'YOUR_GITHUB_TOKEN'),
            "use_https": False,
            "max_retries": 2,
            "skip_uv_install": False,
            "auto_stash": False,
            "sync_only": False,
            "log_file": str(Path.home() / "logs" / "repo-sync.log")
        }
        
        config_path = Path("config.local.json")
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(full_config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 設定ファイルを作成しました: {config_path}")
            print("\\n📋 設定内容:")
            print(f"   👤 GitHubユーザー: {full_config['owner']}")
            print(f"   📁 ワークスペース: {full_config['dest']}")
            print(f"   🔑 トークン: {'設定済み' if full_config['github_token'] != 'YOUR_GITHUB_TOKEN' else '未設定'}")
            
        except OSError as e:
            print(f"❌ 設定ファイルの保存に失敗: {e}")
            return False
        
        return True
    
    def show_next_steps(self):
        """次のステップの案内"""
        print("\\n🎉 セットアップが完了しました!")
        print("=" * 50)
        print("\\n📋 次のステップ:")
        print("  1. 設定確認: cat config.local.json")
        print("  2. テスト実行: uv run main.py sync --dry-run")
        print("  3. 実際の同期: uv run main.py sync")
        
        if self.config.get('github_token') == 'YOUR_GITHUB_TOKEN':
            print("\\n⚠️  GitHubトークンが未設定です:")
            print("   • GitHub CLI: gh auth login")
            print("   • 環境変数: export GITHUB_TOKEN=your_token")
            print("   • 設定ファイル: config.local.json を編集")
        
        print("\\n📚 詳細情報:")
        print("   • README.md - 使用方法")
        print("   • docs/ - 詳細ドキュメント")
        print("\\n🚀 準備完了です! Happy coding! 🎯")
    
    def run(self) -> bool:
        """セットアップウィザードの実行"""
        try:
            self.welcome_message()
            
            if not self.check_prerequisites():
                return False
            
            if not self.setup_package_managers():
                return False
            
            if not self.install_tools():
                return False
            
            self.configure_github()
            self.configure_workspace()
            
            if not self.save_config():
                return False
            
            self.show_next_steps()
            return True
            
        except KeyboardInterrupt:
            print("\\n\\n🛑 セットアップが中断されました")
            return False
        except Exception as e:
            print(f"\\n❌ 予期しないエラーが発生しました: {e}")
            return False
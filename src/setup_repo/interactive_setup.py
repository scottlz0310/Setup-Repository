"""インタラクティブセットアップ機能"""

import json
import subprocess
from pathlib import Path

from .platform_detector import PlatformDetector, get_available_package_managers, get_install_commands
from .security_helpers import safe_subprocess
from .setup_validators import (
    check_system_requirements,
    validate_directory_path,
    validate_github_credentials,
    validate_setup_prerequisites,
    validate_user_input,
)


class InteractiveSetup:
    """インタラクティブセットアップクラス"""

    def __init__(self):
        self.platform_detector = PlatformDetector()
        self.platform_info = self.platform_detector.get_platform_info()
        self.config = {}
        self.errors = []

    def run_setup(self) -> dict:
        """インタラクティブセットアップを実行"""
        print("🚀 インタラクティブセットアップを開始します...")

        # GitHub認証情報の取得
        github_token = input("GitHubトークンを入力してください: ").strip()
        if not github_token:
            raise ValueError("GitHubトークンは必須です")

        github_username = input("GitHubユーザー名を入力してください: ").strip()
        if not github_username:
            raise ValueError("GitHubユーザー名は必須です")

        # クローン先ディレクトリの設定
        clone_destination = input("リポジトリのクローン先ディレクトリを入力してください: ").strip()
        if not clone_destination:
            clone_destination = "./repos"

        # その他の設定
        auto_install = input("依存関係を自動インストールしますか？ (y/n): ").strip().lower() == "y"
        setup_vscode = input("VS Code設定を適用しますか？ (y/n): ").strip().lower() == "y"

        # 設定を構築
        config = {
            "github_token": github_token,
            "github_username": github_username,
            "clone_destination": clone_destination,
            "auto_install_dependencies": auto_install,
            "setup_vscode": setup_vscode,
            "platform_specific_setup": True,
            "dry_run": False,
            "verbose": True,
        }

        # 設定を保存するか確認
        save_config = input("設定をファイルに保存しますか？ (y/n): ").strip().lower() == "y"
        if save_config:
            config_file = Path("config.local.json")
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✅ 設定を {config_file} に保存しました")

        return config


class SetupWizard:
    """セットアップウィザード"""

    def __init__(self):
        self.platform_detector = PlatformDetector()
        self.platform_info = self.platform_detector.get_platform_info()
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

        prereq_result = validate_setup_prerequisites()

        # 成功した項目を表示
        if prereq_result["python"]["valid"]:
            print(f"✅ Python {prereq_result['python']['version']}")

        if prereq_result["git"]["available"]:
            print(f"✅ {prereq_result['git']['version']}")

        if prereq_result["uv"]["available"]:
            print(f"✅ {prereq_result['uv']['version']}")

        if prereq_result["gh"]["available"]:
            print(f"✅ {prereq_result['gh']['version']}")

        # 警告を表示
        for warning in prereq_result["warnings"]:
            print(f"⚠️  {warning}")

        # エラーがある場合
        if not prereq_result["valid"]:
            print("\\n❌ 前提条件が満たされていません:")
            for error in prereq_result["errors"]:
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
            return response in ["y", "yes", "はい"]

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
            print('  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')

    def install_tools(self) -> bool:
        """必要ツールのインストール"""
        print("\\n🔧 必要ツールをインストール中...")

        # uv チェック
        uv_installed = self._check_tool("uv")
        if not uv_installed and not self._install_uv():
            return False

        # GitHub CLI チェック（オプション）
        gh_installed = self._check_tool("gh")
        if not gh_installed:
            print("⚠️  GitHub CLI が見つかりません（オプション）")
            response = input("GitHub CLI をインストールしますか? 認証が簡単になります (Y/n): ").strip().lower()
            if response not in ["n", "no", "いいえ"]:
                self._install_gh()

        return True

    def _check_tool(self, tool: str) -> bool:
        """ツールの存在チェック"""
        try:
            result = safe_subprocess([tool, "--version"], capture_output=True, text=True, check=True)
            parts = result.stdout.strip().split()
            version = f"{parts[0]} {parts[1] if len(parts) > 1 else ''}"
            print(f"✅ {tool}: {version}")
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
                        # curl の場合は特別処理 - shell=Trueを避けてshlex.splitを使用
                        import shlex

                        # コマンドを安全に分割して実行
                        cmd_parts = shlex.split(cmd)
                        safe_subprocess(cmd_parts, check=True)
                    else:
                        # コマンドを安全に分割して実行
                        cmd_parts = cmd.split()
                        safe_subprocess(cmd_parts, check=True)

                    print("✅ uv のインストールが完了しました")
                    return True

                except subprocess.CalledProcessError:
                    print(f"❌ {manager} でのインストールに失敗")
                    continue

        # フォールバック: pip
        try:
            safe_subprocess(["pip", "install", "uv"], check=True)
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
                    # コマンドを安全に分割して実行
                    cmd_parts = cmd.split()
                    safe_subprocess(cmd_parts, check=True)
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

        # 既存の認証情報をチェック
        credentials = validate_github_credentials()

        # ユーザー名の設定
        username = credentials["username"]
        if not username:
            print("\\n👤 GitHubユーザー名が検出されませんでした")
            username_input = validate_user_input("GitHubユーザー名を入力してください: ", "string", required=True)

            if username_input["valid"]:
                username = username_input["value"]
                # git config に設定
                try:
                    safe_subprocess(["git", "config", "--global", "user.name", username], check=True)
                    print(f"✅ Git設定にユーザー名を保存しました: {username}")
                except subprocess.CalledProcessError:
                    print("⚠️  Git設定の保存に失敗しました")
        else:
            print(f"✅ GitHubユーザー名: {username}")

        self.config["owner"] = username

        # トークンの設定
        token = credentials["token"]
        if not token:
            print("\\n🔐 GitHubトークンが検出されませんでした")
            print("\\n以下の方法でトークンを設定できます:")
            print("  1. GitHub CLI: gh auth login")
            print("  2. 環境変数: export GITHUB_TOKEN=your_token")
            print("  3. 手動設定: config.local.json で後から設定")

            choice_input = validate_user_input(
                "\\n今すぐ GitHub CLI で認証しますか? (Y/n): ",
                "boolean",
                required=False,
                default="y",
            )

            if choice_input["valid"] and choice_input["value"]:
                try:
                    safe_subprocess(["gh", "auth", "login"], check=True)
                    # 再度トークンをチェック
                    updated_credentials = validate_github_credentials()
                    token = updated_credentials["token"]
                    if token:
                        print("✅ GitHub認証が完了しました")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("⚠️  GitHub CLI認証に失敗しました")
        else:
            print("✅ GitHubトークンが検出されました")

        self.config["github_token"] = token or "YOUR_GITHUB_TOKEN"

    def configure_workspace(self):
        """ワークスペース設定"""
        print("\\n📁 ワークスペース設定...")

        default_workspace = str(Path.home() / "workspace")
        print(f"\\nデフォルトのワークスペース: {default_workspace}")

        path_input = validate_user_input(
            "別のパスを使用しますか? (空白でデフォルト): ",
            "string",
            required=False,
            default=default_workspace,
        )

        if path_input["valid"]:
            workspace_path = path_input["value"] or default_workspace

            # ディレクトリの検証と作成
            path_validation = validate_directory_path(workspace_path)

            if path_validation["valid"]:
                if path_validation.get("created"):
                    print(f"✅ ワークスペースディレクトリを作成しました: {workspace_path}")
                else:
                    print(f"✅ ワークスペースディレクトリを確認しました: {workspace_path}")
                self.config["dest"] = str(path_validation["path"])
            else:
                print(f"❌ {path_validation['error']}")
                print(f"デフォルトのワークスペースを使用します: {default_workspace}")
                self.config["dest"] = default_workspace
        else:
            print(f"デフォルトのワークスペースを使用します: {default_workspace}")
            self.config["dest"] = default_workspace

    def save_config(self):
        """設定ファイルの保存"""
        print("\\n💾 設定を保存中...")

        # 完全な設定を構築
        full_config = {
            "owner": self.config.get("owner", "YOUR_GITHUB_USERNAME"),
            "dest": self.config.get("dest", str(Path.home() / "workspace")),
            "github_token": self.config.get("github_token", "YOUR_GITHUB_TOKEN"),
            "use_https": False,
            "max_retries": 2,
            "skip_uv_install": False,
            "auto_stash": False,
            "sync_only": False,
            "log_file": str(Path.home() / "logs" / "repo-sync.log"),
        }

        config_path = Path("config.local.json")

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(full_config, f, indent=2, ensure_ascii=False)

            print(f"✅ 設定ファイルを作成しました: {config_path}")
            print("\\n📋 設定内容:")
            print(f"   👤 GitHubユーザー: {full_config['owner']}")
            print(f"   📁 ワークスペース: {full_config['dest']}")
            token_status = "設定済み" if full_config["github_token"] != "YOUR_GITHUB_TOKEN" else "未設定"
            print(f"   🔑 トークン: {token_status}")

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

        if self.config.get("github_token") == "YOUR_GITHUB_TOKEN":
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


# 後方互換性のためのエイリアス
__all__ = [
    "InteractiveSetup",
    "SetupWizard",
    # バリデーター（後方互換性）
    "validate_github_credentials",
    "validate_directory_path",
    "validate_setup_prerequisites",
    "check_system_requirements",
]

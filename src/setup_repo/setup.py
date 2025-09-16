"""初期セットアップ機能"""

import json
from pathlib import Path
from typing import Any

from .config import load_config
from .github_api import GitHubAPI
from .interactive_setup import SetupWizard
from .platform_detector import PlatformDetector


def setup_dependencies() -> bool:
    """依存関係のセットアップ（後方互換性のため）"""
    wizard = SetupWizard()
    return wizard.check_prerequisites()


def create_personal_config() -> None:
    """個人設定の作成（後方互換性のため）"""
    config_path = Path("config.local.json")

    if config_path.exists():
        print(f"✅ {config_path} は既に存在します")
        return

    # インタラクティブセットアップを実行
    wizard = SetupWizard()
    wizard.run()


def run_interactive_setup() -> bool:
    """インタラクティブセットアップの実行"""
    wizard = SetupWizard()
    return wizard.run()


def setup_repository_environment(config_path: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """リポジトリ環境のセットアップ"""
    # 設定を読み込み
    if config_path:
        # 指定されたパスから設定を読み込み
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                config = json.load(f)
        else:
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    else:
        config = load_config()

    # 必須フィールドの検証
    required_fields = ["github_token", "github_username"]
    for field in required_fields:
        if not config.get(field):
            raise ValueError(f"必須フィールドが不足しています: {field}")

    result = {
        "config": config,
        "platform": None,
        "github_user_info": None,
        "dry_run": dry_run,
    }

    try:
        # プラットフォーム検出
        platform_detector = PlatformDetector()
        platform = platform_detector.detect_platform()
        result["platform"] = platform

        # GitHub API接続テスト
        github_api = GitHubAPI(token=config["github_token"], username=config["github_username"])
        user_info = github_api.get_user_info()
        result["github_user_info"] = user_info

        # ドライランモードでない場合は実際のセットアップを実行
        if not dry_run:
            # クローン先ディレクトリの作成
            clone_destination = config.get("clone_destination")
            if clone_destination:
                Path(clone_destination).mkdir(parents=True, exist_ok=True)

        result["success"] = True

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        raise

    return result

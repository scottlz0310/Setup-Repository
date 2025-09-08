"""初期セットアップ機能"""
from pathlib import Path

from .interactive_setup import SetupWizard


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